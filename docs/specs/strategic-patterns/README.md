# Strategic Analysis Patterns

Reusable analysis recipes the service offers users. Distilled from the
2026-07 session (owner's own natal analysis + Fandorin reverse-physiognomy),
where each was first run by hand, then generalised.

Catalog (data): `backend/services/strategic/knowledge_base/analysis_patterns.json`

## Principle

Every pattern follows the house rule: **deterministic computation first,
symbolic interpretation last, provenance always.** Outputs are `Insight`
objects (`backend/services/strategic/layers.py`) carrying `Source` +
`Confidence`. Disclaimer required; no deterministic language.

| Pattern | Offers the user | MCP tool | Skill | Status |
|---|---|---|---|---|
| `money-contour` | how their money works + ceiling | `money_contour` | `/money-contour` | ✅ implemented |
| `vocation-map` | profession clusters with rationale | `vocation_map` | `/vocation-map` | ✅ implemented |
| `decade-map` | decade year-by-year | `decade_map` | `/decade-map` | ✅ implemented |
| `life-pivots` | validate chart vs life + relocations | `life_pivots` | `/life-pivots` | ✅ implemented |
| `electional-day` | best hours for an action | `electional_day` | `/electional-day` | ✅ implemented |
| `reverse-physiognomy` | character → portrait prompt | `reverse_physiognomy_prompt` | `/character-face` | ✅ implemented |

Deterministic core (astronomy 1.0): 2/8/11 houses with rulers/dignities/
Part of Fortune + linchpin · MC complex + work houses + angularity ·
slow-planet decade scans with returns and angle crossings · dated pivot
windows with relocation markers · Moon-by-half-hour with aspects,
void-of-course, phase, Mercury-retrograde flag · physiognomy KB reverse
lookup (dictionary tier 0.6, `fictional_or_self_only` ethics gate).

## Layering

Patterns 1–5 run on Swiss Ephemeris (already a dependency). Pattern 6 is the
physiognomy service in reverse (feeds `scripts/generate_fandorin_portrait.py`).

Per the hard layering rule, each becomes a **skill** (consumer surface) over
**MCP tools** (`backend/mcp/`) that wrap the deterministic compute in
`backend/services/*`. This catalog is the definitional record; skills/tools
are scaffolded from it.

## Validation loop (life-pivots)

`life-pivots` is the one pattern that *improves per user*: when the user
confirms a dated window landed, that insight upgrades from symbolic (0.8) to
astronomy + user_context convergence (HIGH), and the confirmed hits calibrate
which of the user's sensitive points fire strongest — feeding a sharper
`decade-map` for the same user.

## Implementation

- Engine (deterministic core): `backend/services/strategic/pattern_engine.py`
  — importable without the astrology-service stack (own compact dignity
  table, Moshier mode, no geocoder deps), mirroring `lunar/engine.py`.
- MCP tools: `backend/mcp/tools/strategic_patterns.py`, registered in
  `backend/mcp/server.py` (Phase 10 section). Tools return data + a
  `interpretation_rules_ref` into this catalog; skills interpret, labelled.
- Skills: `.claude/skills/{money-contour,vocation-map,decade-map,life-pivots,electional-day,character-face}/SKILL.md`.
- Tests: `backend/tests/test_strategic_patterns.py` (neutral fixture chart,
  no PII) + registration entries in `backend/tests/test_mcp_smoke.py`.

Birth-place resolution stays in the geo tools (`search_city`,
`validate_birth_data`) — pattern tools take lat/lon/tz, per the layering
rule.
