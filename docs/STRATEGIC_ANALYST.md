# OneiroScope as Strategic Life Cycle Analyst (Phase 7 pivot)

## Why this exists

The "AI horoscope" market is saturated with mediocre players (Co-Star,
Sanctuary, The Pattern, Nebula, …). All of them produce text that
**cannot be verified or falsified**. Competing in that category means
racing to the bottom on price and marketing — and losing to whoever
has more VC money.

OneiroScope's alternative: a **Strategic Life Cycle Analyst** — a
decision-support tool that combines several independent analytical
frameworks (astronomy, age psychology, career cycles, economics, user
biography, and — yes — symbolic astrology) and **explicitly labels
which framework each claim came from**.

This isn't anti-astrology. It's anti-fraud. Astrology stays as a
symbolic / reflective framework. It just doesn't get to pretend it
predicts the future.

## The five hard rules

1. **No deterministic language.** Replace "will / будет / случится"
   with "tends to / traditionally associated with / period associated
   with higher load". Enforced by code (`backend.services.strategic.no_determinism`).

2. **Every claim cites its sources.** Each insight names which layer
   (astronomy, user context, statistical research, symbolism) it came
   from. Enforced by typed `Insight` schema.

3. **Confidence is derived, not declared.** From the source mix:
   - 🟢 HIGH — at least one objective fact OR two independent hard layers
   - 🟡 MEDIUM — at least one computational layer
   - 🔴 LOW — only symbolic / generated narrative
   Enforced by `EvidenceMatrix.compute_confidence`.

4. **Skeptical by default.** When multiple explanations exist, mention
   them. When chart claim disagrees with life context, life context wins.

5. **"Window of opportunity" is engineering, not mysticism.** Define as:
   *"a short period when several independent factors converge in one
   direction"*. NOT "because Jupiter."

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  StrategicAnalystAgent                                    │
│  (synthesizes across layers, produces Evidence Matrix)    │
└──────────┬───────────────────────────────────────────────┘
           │  uses these deterministic MCP tools as inputs
           ▼
┌──────────────────────────────────────────────────────────┐
│  Astronomy layer (HIGH confidence inputs)                 │
│  - compute_transits   (Saturn □ Sun on 2026-09-28)        │
│  - solar_return_chart (SR @ Omiš → Sun in 8th house)      │
│  - astrocartography_scan (Madrid: Jupiter on Desc 2.8°)   │
│  - get_lunar_day      (full moon, day 17)                 │
└──────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│  Symbolic layer (LOW confidence inputs)                   │
│  - generate_horoscope (Western traditional reading)       │
│  - forecast_event     (favorability score)                │
│  - list_dream_symbols (Hall/Van de Castle)                │
└──────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│  User context layer (HIGH confidence inputs)              │
│  - User-supplied biography (job, studies, location,       │
│    goals, recent decisions, finances)                     │
└──────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│  Output: EvidenceMatrix                                   │
│  Each Insight: statement + sources + confidence + actions │
└──────────────────────────────────────────────────────────┘
```

## Code map

| Component | Location | Purpose |
|---|---|---|
| `Layer` enum | `backend/services/strategic/layers.py` | 8 epistemic layers |
| `Insight` model | same | Typed claim + sources + confidence |
| `EvidenceMatrix` | same | Collection + auto-confidence derivation |
| `contains_determinism()` | `backend/services/strategic/no_determinism.py` | Regex guard |
| `soften()` | same | Cleanup helper for LLM output |
| `compute_transits` MCP tool | `backend/mcp/tools/strategic_astro.py` | Exact transit dates |
| `astrocartography_scan` | same | Relocation chart angles |
| `solar_return_chart` | same | SR at chosen location |
| `StrategicAnalystAgent` | `agents/specialists/strategic_agent.py` | The synthesis agent |
| `strategic_system.md` | `agents/prompts/` | The system prompt |

## How an answer is constructed

User asks: *"Should I take a mortgage in Spain or Czech Republic?"*

The Strategic Analyst:

1. **Calls** `validate_birth_data` → confirms user's chart inputs.
2. **Calls** `astrocartography_scan` with Madrid, Lisboa, Praha,
   Klatovy → gets which natal planets fall on which angles for each.
3. **Calls** `compute_transits` for the next 12 months → list of
   exact dates of significant transits.
4. **Constructs** Insight objects:
   - `("Madrid has Jupiter on Desc (orb 2.8°)", [ASTRONOMY], MEDIUM)`
   - `("Iberian banks more open to non-resident mortgages than Czech",
      [ECONOMICS, OBJECTIVE_FACT], HIGH)`
   - `("Jupiter-Desc is traditionally associated with partner support",
      [ASTROLOGY_SYMBOLIC], LOW)`
   - `("Madrid is your strongest 'partner-finance' location by
      convergence of astronomy + economics + user context (sметчик
      seeks construction job)", [ASTRONOMY, ECONOMICS, USER_CONTEXT],
      HIGH)`
5. **Renders** the response with explicit layer labels and confidence
   color codes per claim.
6. **Closes** with: *"Эта модель — инструмент для размышления, не
   доказательство будущего."*

## What this is NOT

- Not a Fortune-Telling app. Forbidden by Hard Rule #1.
- Not a Co-Star clone. Co-Star generates symbolic-only text with no
  source attribution; Strategic Analyst forces source attribution.
- Not academic astrology software. SwePy-based but with a usable
  decision-support layer on top.
- Not free of astrology — astrology is the **reflective layer**, just
  not the **predictive layer**.

## Market positioning

| Axis | "Yet another astro AI" | OneiroScope Strategic Analyst |
|---|---|---|
| TAM | 100M+ casual curious | 1-5M serious self-development |
| ARPU | $5-9/mo | $25-50/mo (premium tier) |
| Defensibility | Low — anyone with an LLM key | High — typed evidence matrix + MCP tools + multi-layer engine |
| Marketing | Viral TikTok / horoscope memes | Long-form content, podcast appearances, B2B for coaches/therapists |
| Direct competitors | Co-Star, Sanctuary, Nebula | **None at this positioning** |

## Recommended product structure

- **Free tier (web)** — classic astrology UI (natal chart, daily
  horoscope, dream analysis) — onboarding funnel.
- **Premium tier** — Strategic Analyst experience: every reading is
  multi-layer with Evidence Matrix UI. $25-50/month.
- **MCP / BYOK** — free, for tech users connecting via Claude Desktop.
  Loss-leader for community.

## How to extend

To add a new analytical layer (e.g. Vedic astrology, Chinese
cycles, biorhythms):

1. Add a value to `Layer` enum.
2. If it's deterministic: classify it in `_HARD_LAYERS` or
   `_STATISTICAL_LAYERS`. If symbolic: leave it in `_SYMBOLIC_LAYERS`.
3. Add an MCP tool that computes the data.
4. The Strategic Analyst will pick it up via tool discovery.

The confidence formula stays the same — convergence across hard layers
boosts HIGH; symbolic-alone stays LOW.
