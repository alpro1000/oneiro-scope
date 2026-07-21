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

| Pattern | Offers the user | Deterministic (1.0) | Symbolic (0.8) |
|---|---|---|---|
| `money-contour` | how their money works + ceiling | 2/8 houses, rulers, dispositors, Part of Fortune, linchpin | earning style, wealth-ceiling domain |
| `vocation-map` | profession clusters with rationale | MC+ruler, 2/6/10, dignities, angularity | 3–5 vocation families + sweet spot |
| `decade-map` | decade year-by-year | slow-planet transits by natal house, returns, angle ingresses | phase themes, launch/harvest windows |
| `life-pivots` | validate chart vs life + relocations | slow planets conj angles/luminaries (dated) | dated pivots; **validation loop → user_context upgrade** |
| `electional-day` | best hours for an action | Moon-by-hour, aspects, void-of-course, phase | begin-vs-release, ruler caution |
| `reverse-physiognomy` | character → portrait prompt | physiognomy KB read in reverse | RU/EN generation + negative prompt |

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

## Next

Each row is ready to scaffold as a skill + MCP tool. Suggested first build:
`money-contour` and `decade-map` (highest user pull, pure-ephemeris, no
external deps).
