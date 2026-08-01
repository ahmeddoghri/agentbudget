"""Tests for the volatile-observation-field blind spot and its fix."""

from __future__ import annotations

import pytest

from agentbudget.adversarial import ADVERSARIAL_TRACES, HOLDOUT_TRACES
from agentbudget.eval_v2 import _run, build_report
from agentbudget.guardrail import BudgetExceeded, BudgetGuardrail
from agentbudget.guardrail_v2 import BudgetGuardrailV2, canonicalize
from agentbudget.traces import TRACES

# --- the finding: exact-match hashing misses volatile-field stalls ---------

def test_original_guardrail_misses_every_adversarial_stall():
    for label, is_stalled, trace in ADVERSARIAL_TRACES:
        assert is_stalled
        _, reason = _run(BudgetGuardrail, trace)
        assert reason != "loop_detected", label


def test_rate_limit_countdown_runs_to_completion_undetected():
    """The concrete motivating case: identical failure, different countdown
    every time, six calls, zero detection."""
    trace = dict((l, t) for l, _, t in ADVERSARIAL_TRACES)["rate_limit_with_countdown"]
    steps, reason = _run(BudgetGuardrail, trace)
    assert reason == "ran_all"
    assert steps == len(trace)


# --- the fix -----------------------------------------------------------------

def test_canonicalize_collapses_duration_countdowns():
    assert canonicalize("retry after 1247ms") == canonicalize("retry after 983ms")


def test_canonicalize_collapses_hex_request_ids():
    assert canonicalize("request a1b2c3d4e5f6 failed") == canonicalize(
        "request 9f8e7d6c5b4a failed"
    )


def test_canonicalize_collapses_iso_timestamps():
    assert canonicalize("build failed at 2026-03-14T09:12:03Z") == canonicalize(
        "build failed at 2026-03-14T09:19:40Z"
    )


def test_canonicalize_leaves_plain_counts_alone():
    """The fix must not blindly strip every digit: "3 tests failed" and "5
    tests failed" describe genuinely different states."""
    assert canonicalize("3 tests failed") != canonicalize("5 tests failed")
    assert canonicalize("config has 12 keys") == "config has 12 keys"


def test_fixed_guardrail_catches_every_adversarial_stall():
    for label, is_stalled, trace in ADVERSARIAL_TRACES:
        _, reason = _run(BudgetGuardrailV2, trace)
        assert reason == "loop_detected", label


def test_fixed_guardrail_does_not_false_positive_on_convergence():
    """A genuinely converging trace (same action, decreasing failure count)
    must not be flagged as a loop just because the action repeats."""
    trace = [
        ("run_tests", "5 tests failed", 0.03),
        ("run_tests", "3 tests failed", 0.03),
        ("run_tests", "1 test failed", 0.03),
        ("run_tests", "0 tests failed, all pass", 0.03),
    ]
    steps, reason = _run(BudgetGuardrailV2, trace)
    assert reason == "ran_all"


# --- zero regression on the original benchmark ------------------------------

def test_fixed_guardrail_reproduces_original_results_exactly():
    for label, is_stalled, trace in TRACES:
        s1, r1 = _run(BudgetGuardrail, trace)
        s2, r2 = _run(BudgetGuardrailV2, trace)
        assert (s1, r1) == (s2, r2), label


# --- held out, evaluated once ------------------------------------------------

def test_holdout_is_disjoint_from_the_tuning_corpus():
    adv_labels = {label for label, _, _ in ADVERSARIAL_TRACES}
    holdout_labels = {label for label, _, _ in HOLDOUT_TRACES}
    assert not (adv_labels & holdout_labels)


def test_holdout_catches_every_stall_with_the_fix():
    for label, is_stalled, trace in HOLDOUT_TRACES:
        if not is_stalled:
            continue
        _, reason = _run(BudgetGuardrailV2, trace)
        assert reason == "loop_detected", label


def test_holdout_misses_every_stall_without_the_fix():
    for label, is_stalled, trace in HOLDOUT_TRACES:
        if not is_stalled:
            continue
        _, reason = _run(BudgetGuardrail, trace)
        assert reason != "loop_detected", label


def test_holdout_converging_trace_never_flags_in_either_version():
    trace = dict((l, t) for l, _, t in HOLDOUT_TRACES)["converging_should_not_flag"]
    s1, r1 = _run(BudgetGuardrail, trace)
    s2, r2 = _run(BudgetGuardrailV2, trace)
    assert r1 == "ran_all"
    assert r2 == "ran_all"


# --- the original module is untouched ---------------------------------------

def test_original_guardrail_module_untouched():
    import agentbudget.guardrail as guardrail_module

    assert not hasattr(guardrail_module, "BudgetGuardrailV2")


def test_original_benchmark_still_reproduces():
    for label, is_stalled, trace in TRACES:
        _, reason = _run(BudgetGuardrail, trace)
        if is_stalled:
            assert reason == "loop_detected", label
        else:
            assert reason == "ran_all", label


def test_hard_limits_still_work_on_v2():
    guard = BudgetGuardrailV2(max_steps=3)
    for i in range(3):
        guard.record(f"action{i}", f"obs{i}", cost=0.01)
        guard.check()
    guard.record("action4", "obs4", cost=0.01)
    with pytest.raises(BudgetExceeded) as exc:
        guard.check()
    assert exc.value.reason == "max_steps"


# --- the full report ---------------------------------------------------------

def test_report_is_reproducible():
    assert build_report() == build_report()
