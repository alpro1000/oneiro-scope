# BUG-{id} — {short title}

> **English TL;DR:** Bug report — what's observed, what's expected,
> reproduction steps, severity. Written by reporter (user or
> Claude during testing).

**Reported:** YYYY-MM-DD
**Reporter:** ...
**Severity:** P0 blocker | P1 critical | P2 normal | P3 nice-to-fix
**Affects:** branch / main / production
**Related:** PR # / issue # / earlier bug #

---

## §1 Observed behaviour

What actually happens. Be concrete.

```
$ python -m agents.cli "Натальная карта на 01.07.1977..."
# Output:
...
```

## §2 Expected behaviour

What SHOULD happen, per `docs/steering/domain.md` rules or per the
spec / requirements.md.

## §3 Reproduction steps (deterministic)

1. ...
2. ...
3. Observe: ...

**Environment:**
- OS: ...
- Python: ...
- Branch / commit: ...
- LLM provider env: ...
- Cloud Run / local / Render?

## §4 Severity rationale

Why P0/P1/P2/P3:
- Breaks paying users? → P0
- Affects free-tier funnel? → P1
- Affects only edge case → P2/P3

## §5 Initial guess at scope (optional)

Where in the codebase you suspect this lives. Don't commit to a fix
here — that's `analyze.md`.

## §6 Domain rule violated (if any)

Cite the rule from `docs/steering/domain.md` or `conventions.md` if
the bug violates an explicit invariant (e.g., "interpretive response
without disclaimer" violates §1).
