---
name: cost-report
description: Report LLM provider costs over a period for OneiroScope MCP/API calls. Use when the user asks "how much have we spent on LLM", "cost report", or invokes /cost-report. Reads from Redis cost-tracker counters if present; otherwise reports that cost tracking is not yet wired (Phase 4 work).
---

# /cost-report — LLM cost report

## What this does

Summarize LLM spend per provider over a period.

## Implementation

`backend/core/cost_tracker.py` records every successful LLM call inside
`UniversalLLMProvider.generate()`. Persists to Redis when `REDIS_URL` is
set, otherwise to an in-memory store (resets on process restart).

Counters per day per provider:
- `calls`, `input_tok`, `output_tok`, `usd_micro` (USD × 1,000,000)

Token counts use a chars/4 heuristic — providers don't return usage,
so the report is an estimate, not a billing source of truth.

To read:

```python
from datetime import date
from backend.core import cost_tracker

rows = cost_tracker.report(date.today(), date.today())
for r in rows:
    print(r.provider, r.calls, r.input_tokens, r.output_tokens, f"${r.usd:.4f}")
```

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
