# BUG-{id} — Verify

> **English TL;DR:** Post-merge verification. Repro test green on
> main; production smoke; soul.md updated.

**Status:** verified | needs-rollback
**Verified by:** {who}
**Date:** YYYY-MM-DD

---

## §1 Test verification

- [ ] Repro test from `analyze.md` § 1 is GREEN on the merged commit.
- [ ] Regression test is GREEN.
- [ ] Full backend suite is GREEN (no new failures introduced).

```
$ python -m pytest backend/tests/
{count} passed, {skipped} skipped in {time}s
```

## §2 Production / staging smoke

If the bug affected a deployed environment, verify there too.

- [ ] Cloud Run / Render deploy succeeded.
- [ ] Reproduction step from `report.md` § 3 no longer reproduces.
- [ ] No new errors in the last hour of logs.

## §3 Disclaimer / domain rule re-check

- [ ] Sample 3 production responses (or representative test outputs)
      and confirm:
  - [ ] All carry disclaimer (`has_disclaimer()`).
  - [ ] None contain forbidden language (`contains_determinism()`).
  - [ ] Each has source attribution.

## §4 Bookkeeping

- [ ] `docs/soul.md §9` updated with entry: "fix(BUG-{id}): ...".
- [ ] `docs/soul.md §5` (known issues) updated if this was a tracked
      pre-existing issue.
- [ ] `docs/next-session.md` updated — remove from "what's broken"
      list.
- [ ] If a domain rule was added/clarified as part of this fix,
      `docs/steering/domain.md` updated.

## §5 What we learned

One-liner. Goes into the team's collective memory.

## §6 If rollback needed

- Commit SHA to revert: ...
- Steps: ...
- Communication: who to notify.
