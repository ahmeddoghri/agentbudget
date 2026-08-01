# 🛑 agentbudget

**Stop your agent before it loops forever and burns your budget.**

![CI](https://github.com/ahmeddoghri/agentbudget/actions/workflows/ci.yml/badge.svg)
![tests](https://img.shields.io/badge/tests-26%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![deps](https://img.shields.io/badge/runtime%20deps-none-success)
![license](https://img.shields.io/badge/license-MIT-black)

> **A step-count-only guardrail catches 0 of 3 stalled agent traces, because
> none of them ever hit a hard ceiling. Loop detection catches all 3, usually
> within a handful of steps.** `python -m agentbudget.eval`.
>
> **Update:** loop detection itself has a blind spot just as common as the
> one it fixes. Exact-match hashing means a stall where the API error
> includes a retry-after countdown, a request ID, or a timestamp, the kind
> of thing real error responses do constantly, produces a different
> observation string every call and is never detected. Six identical
> rate-limit failures ran to completion, undetected. Fixed:
> `python -m agentbudget.eval_v2`.

An agentic loop, plan, call a tool, observe, repeat, has no natural stopping
point, kind of like a group chat that refuses to die. Give it a task it can't
quite finish and it won't crash. It'll do something worse: it'll look busy
forever. It retries the same failing call like insisting harder will change
the API. It bounces between two states like it's stuck in a revolving door.
It cycles through three approaches without ever admitting none of them are
working, and your step counter and your cost counter both sit comfortably
under their limits the entire time, because a stall isn't a runaway, it's a
very well-behaved way to set money on fire.

agentbudget is the guardrail that catches the well-behaved failure too. Hard
limits (steps, dollars, wall-clock) stop the obvious runaway, the agent that's
clearly off the rails. Loop detection catches the sneaky one: it hashes every
(action, observation) pair and flags it the moment the same transition
repeats too many times in a short window, whether or not any hard ceiling was
ever close to tripping.

No model, no network, no dependencies. You call `record()` after every tool
call and `check()` before the next one; it does the rest.

---

## The result in one command

```bash
python -m agentbudget.eval
```
```
agent guardrail benchmark: 5 simulated traces

                         trace      truth     limits only   with loop detection
          completes_in_5_steps  completes       ran all 5             ran all 5
   completes_in_8_steps_varied  completes       ran all 8             ran all 8
      retries_same_broken_call    stalled       ran all 6  stopped@3 (loop_detected)
    bounces_between_two_states    stalled       ran all 7  stopped@6 (loop_detected)
            thrashes_three_way    stalled       ran all 9  stopped@7 (loop_detected)

of 3 stalled traces, limits-only catches 0 (none exceed a hard ceiling), so it
burns every step doing nothing useful on all 3. loop detection catches 3/3.
```

Every stalled trace here stays comfortably under generous step, cost, and time
limits. That is the point: limits-only is not wrong exactly, it is just blind
to the failure that actually costs you money in practice. Loop detection is not
a nice-to-have on top of hard limits. It is the layer that catches what hard
limits cannot see by design, and it never once false-positives on the two
traces that actually complete the task.

## Install

```bash
git clone https://github.com/ahmeddoghri/agentbudget
cd agentbudget && pip install -e .
python examples/quickstart.py
```

## Use it

```python
from agentbudget.guardrail import BudgetExceeded, BudgetGuardrail

guard = BudgetGuardrail(max_steps=50, max_cost=5.0, loop_repeat_threshold=3)

while not task_done:
    action, observation, cost = agent.step()
    guard.record(action, observation, cost)
    try:
        guard.check()
    except BudgetExceeded as e:
        print(f"stopping: {e.reason} ({e.detail})")
        break
```

## How loop detection works

```
for each step: hash (action, observation) into a signature
look back over the last `loop_window` steps
if any signature appears `loop_repeat_threshold` or more times -> stall detected
```

That is the whole algorithm. It is intentionally simple: no embeddings, no
similarity threshold to tune, just exact repeats of the same action producing
the same result. That simplicity is a feature. An agent that is truly stuck
repeats itself in ways that are easy to catch exactly; you do not need
semantic fuzziness to find "I called the same broken thing five times in a
row."

## A volatile field in the observation defeats it just as easily

There's a second gap in the exact-match design, more common than the agent
varying its own wording, and it comes from the environment, not the agent.
Real API errors routinely embed a field that changes on every call even
when the underlying situation is identical: a retry-after countdown, a
request ID, a timestamp.

```
"error: rate limited, retry after 1247ms"
"error: rate limited, retry after 983ms"
"error: rate limited, retry after 1502ms"
...
```

Six calls to the same broken endpoint, six different observation strings.
`BudgetGuardrail` hashes them as-is: it runs all six steps and never once
flags a loop, exactly the "well-behaved failure" this tool exists to
catch, invisible to it because of one countdown nobody thought to
normalize.

```bash
python -m agentbudget.eval_v2
```
```
corpus / version            caught    recall   false pos
adversarial / v1            0/3           0%           0
adversarial / v2            3/3         100%           0

holdout / v1                 0/2           0%           0
holdout / v2                  2/2         100%           0
```

The fix can't be "strip every digit": some digits in an observation are
the actual progress signal, "5 tests failed" -> "3 tests failed" -> "0
tests failed" is real convergence, and blindly collapsing those would turn
progress into a false loop alarm. `agentbudget/guardrail_v2.py`'s
`canonicalize()` only neutralizes tokens that structurally look volatile:
durations ("1247ms", "3.2s"), ISO-8601 timestamps, UUIDs, and long
hex-looking IDs. A bare count like "3 tests failed" is left untouched, and
a genuinely converging trace with the same action every step never
false-positives in either version, verified directly. 0% to 100% recall on
three adversarial volatile-field patterns and a two-stall holdout
evaluated exactly once, with zero regression on the original five-trace
benchmark. `guardrail.py` is untouched, so `BudgetGuardrail`'s exact-match
behavior and the published numbers above are unaffected; `BudgetGuardrailV2`
is opt-in.

## What it will not catch

If the agent varies its wording each time (different phrasing, same underlying
dead end), exact-match loop detection can miss it. That is a real limitation,
not a hidden one: the fix is a semantic equivalence check at the signature
step, the same idea as [semanticentropy](https://github.com/ahmeddoghri/semanticentropy)
uses for hallucination detection. The hook is there; `StepRecord.signature()`
is the one place to change.

## Tests

```bash
pip install pytest && pytest -q      # 26 passing
```

## License

MIT © Ahmed Doghri
