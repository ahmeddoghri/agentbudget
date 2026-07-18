import pytest

from agentbudget.guardrail import BudgetExceeded, BudgetGuardrail
from agentbudget.traces import TRACES


def test_max_steps_trips():
    guard = BudgetGuardrail(max_steps=3)
    for i in range(3):
        guard.record(f"action{i}", f"obs{i}", cost=0.01)
        guard.check()
    guard.record("action4", "obs4", cost=0.01)
    with pytest.raises(BudgetExceeded) as exc:
        guard.check()
    assert exc.value.reason == "max_steps"


def test_max_cost_trips():
    guard = BudgetGuardrail(max_cost=1.0)
    guard.record("expensive_call", "result", cost=1.5)
    with pytest.raises(BudgetExceeded) as exc:
        guard.check()
    assert exc.value.reason == "max_cost"


def test_healthy_trace_never_trips():
    guard = BudgetGuardrail(max_steps=50, max_cost=5.0)
    for action, observation, cost in TRACES[0][2]:
        guard.record(action, observation, cost)
        guard.check()  # should not raise
    assert guard.steps_taken == len(TRACES[0][2])


def test_loop_detection_catches_exact_repeat():
    guard = BudgetGuardrail(max_steps=50, loop_repeat_threshold=3, loop_window=6)
    for _ in range(2):
        guard.record("call_api", "error: rate limited", cost=0.01)
        guard.check()
    guard.record("call_api", "error: rate limited", cost=0.01)
    with pytest.raises(BudgetExceeded) as exc:
        guard.check()
    assert exc.value.reason == "loop_detected"


def test_loop_detection_ignores_varied_steps():
    guard = BudgetGuardrail(max_steps=50, loop_repeat_threshold=3, loop_window=6)
    for i in range(5):
        guard.record(f"action{i}", f"distinct_observation_{i}", cost=0.01)
        guard.check()  # should never raise: no repeats


def test_loop_window_limits_lookback():
    # two identical steps far apart (outside the window) should not count as a loop
    guard = BudgetGuardrail(max_steps=50, loop_repeat_threshold=2, loop_window=2)
    guard.record("call_api", "error", cost=0.01)
    guard.check()
    guard.record("other_action", "ok", cost=0.01)
    guard.check()
    guard.record("another_action", "ok", cost=0.01)
    guard.check()  # window is only 2, so the earlier "call_api" step has rolled off


def test_cost_accumulates():
    guard = BudgetGuardrail(max_cost=10.0)
    for _ in range(3):
        guard.record("a", "b", cost=0.5)
    assert guard.total_cost == 1.5


def test_stalled_traces_are_caught_by_loop_detection():
    for label, is_stalled, steps in TRACES:
        if not is_stalled:
            continue
        guard = BudgetGuardrail(max_steps=50, max_cost=5.0, loop_repeat_threshold=3)
        tripped = False
        for action, observation, cost in steps:
            guard.record(action, observation, cost)
            try:
                guard.check()
            except BudgetExceeded as e:
                tripped = True
                assert e.reason == "loop_detected"
                break
        assert tripped, f"{label} should have tripped loop detection"


def test_completed_traces_never_trip_loop_detection():
    for label, is_stalled, steps in TRACES:
        if is_stalled:
            continue
        guard = BudgetGuardrail(max_steps=50, max_cost=5.0, loop_repeat_threshold=3)
        for action, observation, cost in steps:
            guard.record(action, observation, cost)
            guard.check()  # should never raise
