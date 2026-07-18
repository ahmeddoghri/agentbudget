"""agentbudget: stop your agent before it loops forever and burns your budget.

An agentic loop (plan, call a tool, observe, repeat) has no natural stopping
point. Give it a task it cannot quite finish and it will happily call the same
tool forty times, or bounce between two states forever, or just keep going
until your API bill notices before you do. The failure is not a crash. It is
much worse: the agent looks busy the entire time.

agentbudget is a small, dependency-free guardrail you wrap around the loop. It
enforces hard limits (step count, wall-clock time, dollar cost) and, more
interestingly, detects the soft failure that a step counter alone misses:
looping between the same handful of states without making progress. It ships a
benchmark comparing a naive step-limit-only guardrail against loop detection on
agent traces where the difference is the whole story.
"""
from agentbudget.guardrail import BudgetExceeded, BudgetGuardrail, StepRecord

__all__ = ["BudgetGuardrail", "BudgetExceeded", "StepRecord"]

__version__ = "0.1.0"
