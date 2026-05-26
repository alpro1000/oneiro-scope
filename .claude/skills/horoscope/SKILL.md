---
name: horoscope
description: Generate a horoscope (daily, weekly, monthly, yearly) via OneiroScope MCP. Use when the user asks for "гороскоп", "horoscope", or "forecast for today/this week/this month". Supports personalization through a previously calculated natal chart UUID.
---

# /horoscope — Horoscope generation

## What this does

1. Determine period: daily / weekly / monthly / yearly.
2. Determine target date (defaults to today).
3. If the user mentions a saved chart UUID or asks for "my horoscope", look
   for `natal_chart_id` in the conversation context and pass it through.
4. Call `mcp__oneiro__generate_horoscope`.
5. Render the summary, three section breakdowns (love, career, health),
   and recommendations. Mention lunar phase + retrograde planets.

## How to invoke

- "Дневной гороскоп на сегодня"
- "Weekly horoscope starting 2026-06-01"
- "/horoscope monthly"
- "Гороскоп для моей натальной карты <uuid>"

## Required inputs

- **period** — daily | weekly | monthly | yearly. Default: daily.

## Optional inputs

- **target_date** — YYYY-MM-DD. Default: today.
- **natal_chart_id** — UUID for personalization.
- **locale** — auto-detected.

## Behavior

- Length: daily/weekly should be 600–1000 words; longer for monthly/yearly.
  If shorter, do NOT pad — report the underlying provider may have been
  truncated.
- Always surface lunar phase and retrograde planets in the summary header.
- For personalized horoscopes, mention which natal placements influenced
  the reading (Sun/Moon/Ascendant).

## Tools used

- `mcp__oneiro__generate_horoscope`
- `mcp__oneiro__list_horoscope_periods` (only if user uses an unknown
  period word)
