"""Simulated agent traces: some finish the task, some stall in a loop.

Each trace is a list of (action, observation, cost) steps as a real agent
would produce them. The "stalled" traces cycle through the same handful of
(action, observation) pairs, exactly what happens when an agent keeps retrying
an approach that is not working. The "completed" traces make steady progress
toward a distinct final observation.

We deliberately keep every trace under the hard step/cost/time limits, so any
difference the guardrail catches is attributable entirely to loop detection,
not to a hard ceiling that would have caught it anyway.
"""
from __future__ import annotations

# (label, is_stalled, [(action, observation, cost), ...])
TRACES: list[tuple[str, bool, list[tuple[str, str, float]]]] = [
    ("completes_in_5_steps", False, [
        ("search_docs", "found 3 candidate files", 0.02),
        ("read_file:config.py", "config has 12 keys", 0.01),
        ("read_file:handler.py", "handler calls process()", 0.01),
        ("run_tests", "2 tests failed", 0.03),
        ("fix_import", "tests now pass", 0.02),
    ]),
    ("completes_in_8_steps_varied", False, [
        ("list_dir", "found src/ and tests/", 0.01),
        ("grep:TODO", "3 matches", 0.01),
        ("read_file:a.py", "TODO on line 12", 0.01),
        ("read_file:b.py", "TODO on line 40", 0.01),
        ("edit_file:a.py", "edit applied", 0.02),
        ("edit_file:b.py", "edit applied", 0.02),
        ("run_tests", "all tests pass", 0.03),
        ("commit", "committed successfully", 0.01),
    ]),
    ("retries_same_broken_call", True, [
        ("call_api:get_user", "error: rate limited", 0.02),
        ("call_api:get_user", "error: rate limited", 0.02),
        ("call_api:get_user", "error: rate limited", 0.02),
        ("call_api:get_user", "error: rate limited", 0.02),
        ("call_api:get_user", "error: rate limited", 0.02),
        ("call_api:get_user", "error: rate limited", 0.02),
    ]),
    ("bounces_between_two_states", True, [
        ("read_file:x.py", "syntax error on line 4", 0.01),
        ("edit_file:x.py", "edit applied", 0.02),
        ("run_tests", "still fails: syntax error on line 4", 0.03),
        ("edit_file:x.py", "edit applied", 0.02),
        ("run_tests", "still fails: syntax error on line 4", 0.03),
        ("edit_file:x.py", "edit applied", 0.02),
        ("run_tests", "still fails: syntax error on line 4", 0.03),
    ]),
    ("thrashes_three_way", True, [
        ("search_docs", "no results", 0.02),
        ("search_web", "no results", 0.02),
        ("ask_clarify", "no response", 0.01),
        ("search_docs", "no results", 0.02),
        ("search_web", "no results", 0.02),
        ("ask_clarify", "no response", 0.01),
        ("search_docs", "no results", 0.02),
        ("search_web", "no results", 0.02),
        ("ask_clarify", "no response", 0.01),
    ]),
]
