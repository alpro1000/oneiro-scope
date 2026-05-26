# Steering — Product

## Vision

OneiroScope = "научная мистика". Mystical UX with rigorous backend: astronomical accuracy (Swiss Ephemeris), peer-reviewed dream methodology (Hall/Van de Castle), reproducible lunar calendar — never invented numbers.

## Audience

Russian-speaking primary, English-speaking secondary. Users curious about astrology / dreams but skeptical of hand-wavy interpretations. They reward precision (degrees, arc seconds, methodology references) and punish "horoscope mush".

## Product principles

1. **No mocks in production.** Every interpretation traces back to data (ephemeris, knowledge base, peer-reviewed norms). If LLM is unavailable, template fallback is honest and informative — never lorem-ipsum.
2. **Bilingual parity.** Every user-facing string in RU and EN. Dream language auto-detected. No "partial" translations shipped.
3. **Mobile-first.** Forms, lunar widgets, dream input — all designed for thumb input first.
4. **Provenance shown.** Natal chart response includes `provenance` block (ephemeris engine, JD-UT, timezone) so users can verify.
5. **Cost-aware AI.** LLM calls cascade cheapest → most expensive. User never waits longer because we tried Anthropic before Groq.
6. **Privacy.** Birth data is sensitive. No telemetry of contents to third parties beyond chosen LLM provider. No analytics of dream text.

## What we DON'T do

- **No prediction-as-fact.** Horoscopes are framed as influences / tendencies, never "you will meet X". Dream interpretations never diagnose.
- **No prohibited esoteric content.** Dream interpreter has a prohibited list (см. `backend/services/dreams/ai/`): no fortune-telling, no curses, no occult diagnosis.
- **No content under 600 words for paid-tier horoscopes.** Brevity = perceived shallowness.
- **No SSR call to `localhost`** when deployed. Always use `RENDER_EXTERNAL_URL`.

## Quality bars

- Horoscope length: 600–1000 words per period (set in prompt templates).
- Natal chart interpretation: 6 structured sections (personality, strengths, challenges, relationships, career, life_purpose).
- Dream analysis: must include symbols + content_analysis + emotion + themes + interpretation + lunar_context + recommendations.
- Provenance: every astrology response includes engine + JD-UT + timezone.

## Skills UX (Claude Code)

Skills are the owner-facing surface. They should feel like CLI commands but with conversation. Each skill:

- States what it will do in one sentence.
- Asks for missing input via `AskUserQuestion` (or natural follow-up).
- Calls MCP tools (not FastAPI).
- Returns a tight summary; offers to drill deeper.
- Updates `docs/soul.md §9` if the session is substantial (≥ 3 tool calls or ≥ 1 architectural change).
