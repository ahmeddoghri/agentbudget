"""The guardrail: hard limits plus loop detection.

Hard limits (steps, cost, wall-clock) catch the obvious runaway. Loop detection
catches the sneakier failure: an agent that stays under every hard limit while
making zero actual progress, cycling through the same three states because it
never learns that the approach is not working.

We detect loops by hashing each step's (action, observation) pair into a
signature and watching for the same signature repeating within a short window.
Three repeats of an identical state transition inside the window is treated as
a stall, not a coincidence.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


class BudgetExceeded(Exception):
    """Raised when a hard limit or the loop detector trips."""

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}")


@dataclass
class StepRecord:
    action: str
    observation: str
    cost: float
    timestamp: float

    def signature(self) -> tuple[str, str]:
        return (self.action, self.observation)


@dataclass
class BudgetGuardrail:
    """Wrap an agent loop and enforce hard limits plus loop detection.

    ``max_steps``, ``max_cost``, and ``max_seconds`` are hard ceilings: cross
    any one and the next ``check()`` call raises. ``loop_window`` is how many
    recent steps we look back over for repeats, and ``loop_repeat_threshold`` is
    how many identical (action, observation) signatures within that window count
    as a stall.
    """

    max_steps: int = 50
    max_cost: float = 5.0
    max_seconds: float = 300.0
    loop_window: int = 9
    loop_repeat_threshold: int = 3

    _steps: list[StepRecord] = field(default_factory=list, repr=False)
    _start_time: float = field(default=None, repr=False)
    _total_cost: float = field(default=0.0, repr=False)

    def __post_init__(self) -> None:
        self._start_time = time.monotonic()

    def record(self, action: str, observation: str, cost: float = 0.0,
               now: float | None = None) -> None:
        """Log one agent step. Call this after every tool call."""
        ts = now if now is not None else time.monotonic()
        self._steps.append(StepRecord(action, observation, cost, ts))
        self._total_cost += cost

    def check(self) -> None:
        """Raise BudgetExceeded if any hard limit or the loop detector trips.

        Call this after every ``record()``, before letting the agent take
        another step.
        """
        n = len(self._steps)
        if n > self.max_steps:
            raise BudgetExceeded("max_steps", f"{n} steps taken, limit is {self.max_steps}")

        if self._total_cost > self.max_cost:
            raise BudgetExceeded(
                "max_cost", f"${self._total_cost:.2f} spent, limit is ${self.max_cost:.2f}")

        elapsed = (self._steps[-1].timestamp if self._steps else time.monotonic()) - self._start_time
        if elapsed > self.max_seconds:
            raise BudgetExceeded(
                "max_seconds", f"{elapsed:.0f}s elapsed, limit is {self.max_seconds:.0f}s")

        loop_sig = self._detect_loop()
        if loop_sig is not None:
            action, observation = loop_sig
            raise BudgetExceeded(
                "loop_detected",
                f"action {action!r} -> observation {observation!r} repeated "
                f"{self.loop_repeat_threshold}+ times in the last {self.loop_window} steps",
            )

    def _detect_loop(self) -> tuple[str, str] | None:
        recent = self._steps[-self.loop_window:]
        counts: dict[tuple[str, str], int] = {}
        for step in recent:
            sig = step.signature()
            counts[sig] = counts.get(sig, 0) + 1
            if counts[sig] >= self.loop_repeat_threshold:
                return sig
        return None

    @property
    def steps_taken(self) -> int:
        return len(self._steps)

    @property
    def total_cost(self) -> float:
        return self._total_cost
