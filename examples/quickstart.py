"""Sixty-second tour of agentbudget.

    python examples/quickstart.py
"""
from agentbudget.guardrail import BudgetExceeded, BudgetGuardrail

guard = BudgetGuardrail(max_steps=50, max_cost=5.0, loop_repeat_threshold=3)

# Simulate an agent stuck retrying the same failing call.
steps = [
    ("call_api:get_user", "error: rate limited", 0.02),
    ("call_api:get_user", "error: rate limited", 0.02),
    ("call_api:get_user", "error: rate limited", 0.02),
    ("call_api:get_user", "error: rate limited", 0.02),   # would never get here
]

for action, observation, cost in steps:
    guard.record(action, observation, cost)
    try:
        guard.check()
    except BudgetExceeded as e:
        print(f"stopped after {guard.steps_taken} steps: {e.reason}")
        print(f"detail: {e.detail}")
        break
else:
    print("agent ran to completion")
