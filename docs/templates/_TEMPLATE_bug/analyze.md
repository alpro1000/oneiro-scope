# BUG-{id} — Analysis

> **English TL;DR:** Root-cause investigation. Reproducible repro
> committed. Hypotheses generated and adversarially tested. Final
> verdict + smallest-possible-fix scope.

**Status:** investigating | rcc-found | fix-spec-ready
**Updated:** YYYY-MM-DD

---

## §1 Repro lock-in

Failing test or script that reproduces the bug — **commit it before
investigating**. Without this, you'll fix the wrong thing.

```python
# backend/tests/test_bug_{id}_repro.py
def test_repro():
    # Should fail BEFORE fix, pass AFTER.
    ...
```

Commit: `test: lock repro for BUG-{id}`

## §2 Hypotheses (multiple — generate at least 3)

| # | Hypothesis | How to refute | Status |
|---|---|---|---|
| 1 | The disclaimer is missing because `ensure_disclaimer` isn't called | Add print at function entry | refuted / confirmed / pending |
| 2 | LLM provider returns text already containing disclaimer in some locales | Check `has_disclaimer()` on raw LLM output | ... |
| 3 | Timezone shift caused planet position drift | Compare JD with `zoneinfo` vs `pytz` | ... |

**Bias check:** which hypothesis am I rooting for, and why? Bias
toward "easy fix" is the most common trap. Force yourself to test
the EXPENSIVE hypothesis first.

## §3 Investigation log

Timestamped notes on what you tried:

- HH:MM — checked X, found Y.
- HH:MM — instrumented Z, observed W.

## §4 Root cause

What actually caused this. **Single sentence.** If you can't compress
it to one sentence, you haven't found the root cause yet.

## §5 Why we didn't catch this earlier

- Missing test for ... → add as part of the fix.
- Code path was added in PR # without an integration test.
- Documentation was outdated.

## §6 Fix scope (smallest possible)

What to change, in which file, with what semantics. **Don't write
the patch here** — that's `fix.md`.

- File: `backend/services/X/y.py`, line N.
- Change: ...
- Side-effects on other code: ...
- Tests to add: ...

## §7 Risks of the fix

What this change could break. Always non-empty for non-trivial bugs.
