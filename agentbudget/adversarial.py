"""Stalled traces where a volatile field in the observation defeats
exact-match loop detection.

The bundled benchmark's stalled traces repeat byte-identical observation
strings every time, which is convenient for the demo but not how a real
API error usually looks. Real error responses commonly embed a field that
changes on every call regardless of whether the underlying situation
changed at all: a retry-after countdown, a request ID, a timestamp. None
of these adversarial traces repeat a single identical string; every one
of them is, underneath the volatile field, the exact same well-behaved
stall the bundled benchmark already claims to catch.
"""
from __future__ import annotations

# (label, is_stalled, [(action, observation, cost), ...])
ADVERSARIAL_TRACES: list[tuple[str, bool, list[tuple[str, str, float]]]] = [
    ("rate_limit_with_countdown", True, [
        ("call_api:get_user", "error: rate limited, retry after 1247ms", 0.02),
        ("call_api:get_user", "error: rate limited, retry after 983ms", 0.02),
        ("call_api:get_user", "error: rate limited, retry after 1502ms", 0.02),
        ("call_api:get_user", "error: rate limited, retry after 611ms", 0.02),
        ("call_api:get_user", "error: rate limited, retry after 1899ms", 0.02),
        ("call_api:get_user", "error: rate limited, retry after 734ms", 0.02),
    ]),
    ("timeout_with_request_id", True, [
        ("call_api:submit_order", "error: timeout, request a1b2c3d4e5f6 failed", 0.02),
        ("call_api:submit_order", "error: timeout, request 9f8e7d6c5b4a failed", 0.02),
        ("call_api:submit_order", "error: timeout, request 001122334455 failed", 0.02),
        ("call_api:submit_order", "error: timeout, request ffeeddccbbaa failed", 0.02),
    ]),
    ("stuck_build_with_timestamp", True, [
        ("run_build", "build failed at 2026-03-14T09:12:03Z", 0.03),
        ("run_build", "build failed at 2026-03-14T09:14:51Z", 0.03),
        ("run_build", "build failed at 2026-03-14T09:17:22Z", 0.03),
        ("run_build", "build failed at 2026-03-14T09:19:40Z", 0.03),
    ]),
]

# Written after guardrail_v2's canonicalization patterns were frozen against
# ADVERSARIAL_TRACES above. Evaluated exactly once.
HOLDOUT_TRACES: list[tuple[str, bool, list[tuple[str, str, float]]]] = [
    ("db_connection_uuid", True, [
        ("connect_db", "connection refused, session f47ac10b-58cc-4372-a567-0e02b2c3d479", 0.02),
        ("connect_db", "connection refused, session 6ba7b810-9dad-11d1-80b4-00c04fd430c8", 0.02),
        ("connect_db", "connection refused, session 6ba7b812-9dad-11d1-80b4-00c04fd430c8", 0.02),
    ]),
    ("polling_with_elapsed_seconds", True, [
        ("check_job_status", "still running, elapsed 4.2s", 0.01),
        ("check_job_status", "still running, elapsed 9.7s", 0.01),
        ("check_job_status", "still running, elapsed 15.1s", 0.01),
        ("check_job_status", "still running, elapsed 20.6s", 0.01),
    ]),
    # a genuinely converging trace with the same action every step, real
    # decreasing counts -- must NOT be flagged, the false-positive check.
    ("converging_should_not_flag", False, [
        ("run_tests", "5 tests failed", 0.03),
        ("run_tests", "3 tests failed", 0.03),
        ("run_tests", "1 test failed", 0.03),
        ("run_tests", "0 tests failed, all pass", 0.03),
    ]),
]
