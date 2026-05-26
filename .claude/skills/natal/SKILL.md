---
name: natal
description: Compute a natal (birth) chart through the OneiroScope MCP server. Use when the user asks for a "natal chart", "натальная карта", or supplies birth date + place (with optional time). Validates inputs first, then calls calculate_natal_chart, returns a structured summary with provenance.
---

# /natal — Natal chart workflow

## What this does

End-to-end natal chart calculation using OneiroScope MCP tools:

1. Parse birth data from the user message (date, place, optional time).
2. Call `mcp__oneiro__validate_birth_data` to check the date parses and the
   place geocodes. If it fails, ask the user to correct, do NOT guess.
3. Call `mcp__oneiro__calculate_natal_chart` with the validated inputs.
4. Summarize: Sun/Moon/Ascendant signs, key planet placements, 1–2
   structured interpretation sections, and provenance (ephemeris engine,
   resolved location, timezone).
5. Offer to drill into a section (relationships, career, life purpose) or
   generate a personalized horoscope based on this chart.

## How to invoke

User says any of:
- "Натальная карта для 15 мая 1990, Москва, 14:30"
- "Compute my natal chart: 1990-05-15 14:30 Moscow"
- "/natal 1990-05-15 14:30 Moscow"

## Required inputs

- **birth_date** — YYYY-MM-DD or natural language ("15 мая 1990").
- **birth_place** — city name; country optional.

## Optional inputs

- **birth_time** — HH:MM. Without it, 12:00 noon is used and
  Ascendant/houses are omitted from the response.
- **locale** — "ru" or "en". Default: detect from the user message.

## Behavior

- If birth time is missing, **ask once** before falling back to noon.
- If the place is ambiguous (e.g., "Springfield"), call `search_city`
  first and present the top match for confirmation.
- Always include provenance in the final summary: ephemeris engine
  (SWIEPH or MOSEPH), resolved location with timezone.
- Never invent planet positions if the tool errors — report the error.

## Tools used

- `mcp__oneiro__validate_birth_data`
- `mcp__oneiro__search_city` (only if place is ambiguous)
- `mcp__oneiro__calculate_natal_chart`

## Closing step

If this is the only task in the session, append an entry to
`docs/soul.md §9` (Session log) before finishing.
