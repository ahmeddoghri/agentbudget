# 🛑 agentbudget

**Stop your agent before it loops forever and burns your budget.**

![CI](https://github.com/ahmeddoghri/agentbudget/actions/workflows/ci.yml/badge.svg)
![tests](https://img.shields.io/badge/tests-9%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![deps](https://img.shields.io/badge/runtime%20deps-none-success)
![license](https://img.shields.io/badge/license-MIT-black)

> **A step-count-only guardrail catches 0 of 3 stalled agent traces, because
> none of them ever hit a hard ceiling. Loop detection catches all 3, usually
> within a handful of steps.** `python -m agentbudget.eval`.

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

## What it will not catch

If the agent varies its wording each time (different phrasing, same underlying
dead end), exact-match loop detection can miss it. That is a real limitation,
not a hidden one: the fix is a semantic equivalence check at the signature
step, the same idea as [semanticentropy](https://github.com/ahmeddoghri/semanticentropy)
uses for hallucination detection. The hook is there; `StepRecord.signature()`
is the one place to change.

## Tests

```bash
pip install pytest && pytest -q      # 9 passing
```

## License

MIT © Ahmed Doghri
