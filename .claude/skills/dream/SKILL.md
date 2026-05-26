---
name: dream
description: Analyze a dream using Hall/Van de Castle content analysis + Jungian archetypes + REM/NREM models + DreamBank norms via OneiroScope MCP. Use when the user describes a dream ("мне приснилось", "I dreamt that...") or invokes /dream. Auto-detects language and returns structured symbols, themes, interpretation, and recommendations.
---

# /dream — Dream analysis

## What this does

1. Capture the dream narrative (≥ 10 characters, ≤ 10000).
2. Optionally collect: dream date (enables lunar context), dreamer gender
   (enables Hall/Van de Castle norm comparison), age group.
3. Call `mcp__oneiro__analyze_dream`.
4. Present: primary emotion, themes, key symbols (with archetype links),
   norm-comparison findings (if gender given), lunar context (if date
   given), narrative interpretation, recommendations.
5. Offer to look up specific symbols in detail via `list_dream_symbols`
   or list available archetypes via `list_archetypes`.

## How to invoke

- "Мне приснилось, что я лечу над городом..."
- "I dreamt I was being chased through a forest..."
- "/dream <narrative>"

## Required inputs

- **dream_text** — the narrative itself.

## Optional inputs

- **dream_date** — YYYY-MM-DD of the dream.
- **dreamer_gender** — "male" / "female" (enables norm comparison).
- **dreamer_age_group** — e.g. "20-30".
- **locale** — auto-detect from dream language; honor explicit override.

## Behavior

- Language detected from the dream text itself; respond in the same
  language by default.
- If user provides gender, include the typicality score (0–100%) and
  any notable deviations from H/VdC norms.
- Never diagnose medical or psychiatric conditions.
- Never trade in fortune-telling, curses, or occult diagnosis — the
  underlying interpreter explicitly forbids these.

## Tools used

- `mcp__oneiro__analyze_dream`
- `mcp__oneiro__list_dream_symbols` (for follow-up symbol lookups)
- `mcp__oneiro__list_archetypes`
- `mcp__oneiro__list_hvdc_categories`
