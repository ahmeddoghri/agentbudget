"""Does loop detection survive a volatile field in the observation?

``agentbudget.eval`` proves loop detection catches a stall when the
observation repeats byte-for-byte. Real API errors rarely repeat exactly:
a retry-after countdown, a request ID, a timestamp changes on every call
even when the underlying situation is identical. This module reruns the
same stall-detection measurement against :mod:`agentbudget.adversarial`'s
traces (every one is a genuine stall wearing a different volatile field
each step) for both the original exact-match guardrail and the
canonicalizing one.

    python -m agentbudget.eval_v2
"""
from __future__ import annotations

import argparse
import json
from typing import Dict, List, Sequence

from .adversarial import ADVERSARIAL_TRACES, HOLDOUT_TRACES
from .guardrail import BudgetExceeded, BudgetGuardrail
from .guardrail_v2 import BudgetGuardrailV2


def _run(guard_cls, trace: Sequence[tuple]) -> tuple[int, str]:
    guard = guard_cls(max_steps=50, max_cost=5.0, loop_repeat_threshold=3, loop_window=9)
    for i, (action, observation, cost) in enumerate(trace, 1):
        guard.record(action, observation, cost)
        try:
            guard.check()
        except BudgetExceeded as e:
            return i, e.reason
    return guard.steps_taken, "ran_all"


def _score(traces: Sequence[tuple], guard_cls) -> Dict:
    caught = 0
    misses: List[str] = []
    false_positives: List[str] = []
    for label, is_stalled, trace in traces:
        _, reason = _run(guard_cls, trace)
        flagged = reason == "loop_detected"
        if is_stalled and flagged:
            caught += 1
        elif is_stalled and not flagged:
            misses.append(label)
        elif not is_stalled and flagged:
            false_positives.append(label)
    n_stalled = sum(1 for _, s, _ in traces if s)
    return {
        "caught": caught,
        "n_stalled": n_stalled,
        "recall": round(caught / n_stalled, 4) if n_stalled else None,
        "misses": misses,
        "false_positives": false_positives,
    }


def build_report() -> Dict:
    return {
        "adversarial": {
            "v1": _score(ADVERSARIAL_TRACES, BudgetGuardrail),
            "v2": _score(ADVERSARIAL_TRACES, BudgetGuardrailV2),
        },
        "holdout": {
            "v1": _score(HOLDOUT_TRACES, BudgetGuardrail),
            "v2": _score(HOLDOUT_TRACES, BudgetGuardrailV2),
        },
    }


def format_report(report: Dict) -> str:
    lines = [
        "stall recall on traces with a volatile observation field",
        "=" * 60,
        f"{'corpus / version':<22}{'caught':>12}{'recall':>10}{'false pos':>12}",
        "-" * 60,
    ]
    for corpus_name in ("adversarial", "holdout"):
        for v in ("v1", "v2"):
            row = report[corpus_name][v]
            lines.append(
                f"{corpus_name + ' / ' + v:<22}{row['caught']:>7}/{row['n_stalled']:<4}"
                f"{row['recall']:>10.0%}{len(row['false_positives']):>12}"
            )
        lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)

    report = build_report()
    print(format_report(report))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
