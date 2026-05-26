---
name: lunar
description: Get lunar-day information (lunar day number, Moon phase, Moon sign, illumination, themes, recommendations) for a specific date or date range via OneiroScope MCP. Use when the user asks "what lunar day is today", "лунный календарь", or invokes /lunar.
---

# /lunar — Lunar calendar lookup

## What this does

Pure (no-LLM) lunar-day information from Swiss Ephemeris (or Moshier
fallback) plus the bilingual narrative content from `lunar_tables.json`.

- Single date: `mcp__oneiro__get_lunar_day(target_date, timezone, locale)`
- Range (≤ 60 days): `mcp__oneiro__get_lunar_period(start, end, ...)`

## How to invoke

- "Лунный день на сегодня"
- "What lunar day is it on 2026-06-15?"
- "Lunar info for next 7 days, timezone Europe/Berlin"
- "/lunar 2026-06-15"

## Required inputs

- **target_date** (single) OR **start_date** + **end_date** (range).

## Optional inputs

- **timezone** — IANA (e.g. "Europe/Moscow"). Default:
  `LUNAR_DEFAULT_TZ` env var or `Europe/Moscow`.
- **locale** — "ru" / "en" for narrative content.
- **include_content** — only for ranges; default false (just astronomy).

## Behavior

- Always include provenance (engine, JD-UT, timezone) in the response.
- For ranges, summarize first (e.g. "7 days: lunar days 12–18, phases
  waxing→full") then offer to expand any specific day.
