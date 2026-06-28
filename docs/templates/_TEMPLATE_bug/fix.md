# BUG-{id} — Fix

> **English TL;DR:** Implementation of the minimal fix from
> `analyze.md`. Diff summary, tests added, commits.

**Status:** in-progress | merged | reverted
**Branch:** `claude/fix-bug-{id}-{rand5}`
**Updated:** YYYY-MM-DD

---

## §1 Patch summary

```
file1.py | 5 ++--
file2.py | 12 +++++++-
2 files changed, 14 insertions(+), 3 deletions(-)
```

One sentence per file describing what changed.

## §2 Tests added

- `test_bug_{id}_repro` — the original failing repro now passes.
- `test_bug_{id}_regression` — locks in the invariant going forward.
- (Optional) integration test exercising the surrounding flow.

## §3 What we explicitly did NOT change

- Did not refactor surrounding code (Karpathy rule: don't touch what
  the task doesn't require).
- Did not change public API.
- Did not add new dependencies.

If you DID change any of these, justify here.

## §4 Domain rules re-verified post-fix

- [ ] `has_disclaimer()` still True for affected endpoints.
- [ ] `contains_determinism()` returns `[]` for affected text.
- [ ] Provenance (source) still attached to affected outputs.
- [ ] No new deterministic-prediction language in interpretive text.

## §5 Commits

- `test: lock repro for BUG-{id}` (Gate 1 of bug workflow)
- `fix({scope}): {one-line summary} (BUG-{id})`
- `test: add regression test for BUG-{id}`
- `docs: update CHANGELOG / soul.md §9 for BUG-{id}`

## §6 PR notes (auto-generated body)

Use the standard format:
- Summary (2-3 sentences)
- Root cause (one sentence)
- Test plan checklist
- Links: report.md, analyze.md
