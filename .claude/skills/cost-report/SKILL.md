---
name: cost-report
description: Report LLM provider costs over a period for OneiroScope MCP/API calls. Use when the user asks "how much have we spent on LLM", "cost report", or invokes /cost-report. Reads from Redis cost-tracker counters if present; otherwise reports that cost tracking is not yet wired (Phase 4 work).
---

# /cost-report — LLM cost report

## What this does

Summarize LLM spend per provider over a period.

## Implementation status

**Phase 4 work — partially implemented.** The cost-tracker module
(`backend/core/cost_tracker.py`) is NOT yet wired into the LLM
provider abstraction. When invoked today, this skill should:

1. Check whether `backend/core/cost_tracker.py` exists.
2. If yes, read counters from Redis (keys `oneiro:cost:<provider>:<YYYY-MM-DD>`).
3. If no, report "cost tracking not yet wired — tracked in
   `docs/PLAN.md` Phase 4 and `docs/soul.md §5`".

## Inputs

- **period** — `today` | `week` | `month` | `YYYY-MM-DD..YYYY-MM-DD`.
- **provider** — filter to one of groq / gemini / openai / anthropic /
  together. Default: all.

## Output format

```
Provider   | Calls | Tokens (in/out)        | Estimated cost
-----------|-------|------------------------|---------------
Groq       |   42  | 31,400 / 28,100        | $0.00 (free tier)
Gemini     |    8  |  6,200 /  5,400        | $0.0009
OpenAI     |    0  |        — /        —    | $0.00
-----------|-------|------------------------|---------------
TOTAL      |   50  | 37,600 / 33,500        | $0.0009
```

## Behavior

- Estimated cost = tokens × per-1M-token rate from
  `docs/steering/tech.md` LLM provider table.
- If Redis is unreachable, report that explicitly; do NOT silently show
  zero.
