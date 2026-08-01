"""Loop detection that survives a volatile observation field.

``StepRecord.signature()`` hashes the raw ``(action, observation)`` pair.
That's exact-match by design, and the README frames its only known gap as
semantic: an agent that varies its own wording each retry. That's real,
but it's not the failure that actually breaks this in practice. Real API
error responses routinely embed a field that changes on every call even
though the underlying situation is identical: a retry-after countdown, a
request ID, a timestamp.

    "error: rate limited, retry after 1247ms"
    "error: rate limited, retry after 983ms"
    "error: rate limited, retry after 1502ms"
    ...

Six calls to the same broken endpoint, six different observation strings,
because the millisecond countdown is never the same twice. Fed through
``BudgetGuardrail`` as-is: it runs all six steps and never once flags a
loop, the exact class of "well-behaved failure" this tool exists to catch,
invisible to it because of one volatile substring nobody thought to
normalize.

The fix cannot be "strip every digit": some digits in an observation are
the actual progress signal ("5 tests failed" -> "3 tests failed" -> "0
tests failed" is real convergence, not noise, and blindly collapsing those
would turn genuine progress into a false loop alarm). ``canonicalize``
only neutralizes tokens that structurally look volatile: durations
("1247ms", "3.2s"), ISO-8601 timestamps, UUIDs, and long hex-looking IDs.
A bare count like "12" or "3" next to an ordinary word is left alone.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from .guardrail import BudgetExceeded, BudgetGuardrail

_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_ISO_TS = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?\b")
_DURATION = re.compile(
    r"\b\d+(\.\d+)?\s*(ms|s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)\b",
    re.IGNORECASE,
)
_HEX_ID = re.compile(r"\b[0-9a-fA-F]{8,}\b")


def canonicalize(text: str) -> str:
    text = _UUID.sub("<id>", text)
    text = _ISO_TS.sub("<timestamp>", text)
    text = _DURATION.sub("<duration>", text)
    text = _HEX_ID.sub("<id>", text)
    return text


@dataclass
class StepRecordV2:
    action: str
    observation: str
    cost: float
    timestamp: float

    def signature(self) -> tuple[str, str]:
        return (self.action, canonicalize(self.observation))


@dataclass
class BudgetGuardrailV2(BudgetGuardrail):
    """Same interface as :class:`~agentbudget.guardrail.BudgetGuardrail`,
    with loop-detection signatures canonicalized against volatile fields."""

    def record(self, action: str, observation: str, cost: float = 0.0,
               now: float | None = None) -> None:
        ts = now if now is not None else time.monotonic()
        self._steps.append(StepRecordV2(action, observation, cost, ts))
        self._total_cost += cost

    def check(self) -> None:
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
