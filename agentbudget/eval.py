"""Benchmark: does loop detection catch stalls that hard limits miss?

We replay each simulated trace through two guardrail configurations:

  - limits_only: generous step/cost/time ceilings, no loop detection
  - with_loop_detection: the same ceilings, plus the loop detector

Every trace in the corpus stays comfortably under the hard limits (that is
deliberate), so limits_only never stops a stalled trace early. The only
question is whether loop detection catches the stall before it burns through
the whole step budget doing nothing.

Run it:

    python -m agentbudget.eval

Deterministic. No model, no network, no API keys.
"""
from __future__ import annotations

from agentbudget.guardrail import BudgetExceeded, BudgetGuardrail
from agentbudget.traces import TRACES


def _replay(trace, loop_detection: bool) -> tuple[bool, int, str]:
    """Replay a trace through the guardrail. Returns (stopped_early, steps_run, reason)."""
    guard = BudgetGuardrail(
        max_steps=50, max_cost=5.0, max_seconds=300.0,
        loop_repeat_threshold=3 if loop_detection else 10_000,  # effectively off
    )
    for i, (action, observation, cost) in enumerate(trace, start=1):
        guard.record(action, observation, cost)
        try:
            guard.check()
        except BudgetExceeded as e:
            return True, i, e.reason
    return False, len(trace), "completed"


def run() -> None:
    print(f"agent guardrail benchmark: {len(TRACES)} simulated traces\n")
    print(f"  {'trace':>28}  {'truth':>9}  {'limits only':>14}  {'with loop detection':>20}")

    wasted_without = 0
    caught_with = 0
    n_stalled = sum(1 for _, is_stalled, _ in TRACES if is_stalled)

    for label, is_stalled, steps in TRACES:
        stopped_a, run_a, reason_a = _replay(steps, loop_detection=False)
        stopped_b, run_b, reason_b = _replay(steps, loop_detection=True)

        truth = "stalled" if is_stalled else "completes"
        col_a = f"ran all {run_a}" if not stopped_a else f"stopped@{run_a} ({reason_a})"
        col_b = f"ran all {run_b}" if not stopped_b else f"stopped@{run_b} ({reason_b})"
        print(f"  {label:>28}  {truth:>9}  {col_a:>14}  {col_b:>20}")

        if is_stalled and not stopped_a:
            wasted_without += 1
        if is_stalled and stopped_b:
            caught_with += 1

    print(f"\nof {n_stalled} stalled traces, limits-only catches 0 (none exceed a hard")
    print(f"ceiling), so it burns every step doing nothing useful on all {wasted_without}.")
    print(f"loop detection catches {caught_with}/{n_stalled}, stopping the agent within a")
    print("few steps of it starting to repeat itself instead of after the whole budget")
    print("is gone.")


if __name__ == "__main__":
    run()
