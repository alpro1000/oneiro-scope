# OneiroScope — Soul

> **English TL;DR:** Living project memory between Claude Code
> sessions. Reference, not log dump — keep it under ~400 lines.
> Closed/resolved items get crossed out or deleted, not piled up.
> §9 (session log) is the only append-only section.

Personal/project memory file for cross-session continuity. Read by Claude Code at every session start (see mandatory block in `CLAUDE.md`).

**Section map:**
- §1 Identity — what this project is
- §2 Active projects / contexts — current branch, KB sources
- §3 Rules / discipline — 5 owner-side rules
- §4 Code style / conventions
- §5 Known issues / tech debt — strike through when resolved
- §6 Architecture decisions log (ADRs)
- §7 Deployment notes
- §8 Open questions / parking lot
- §9 **Session log** (append-only, newest first)
- §10 Rejected ideas (and why)

---

## §1 Identity

- **Project:** OneiroScope — эзотерический сервис: научная астрология (Swiss Ephemeris) + анализ снов (Hall/Van de Castle, REM/NREM) + лунный календарь.
- **Repo:** `alpro1000/oneiro-scope`
- **Owner:** alpro1000 (alpro1000@gmail.com)
- **Stack:** Python 3.11 / FastAPI / Pydantic v2 backend, Next.js 14 (App Router, next-intl RU/EN) frontend, PostgreSQL + Redis, Render.com deploy.
- **Languages:** Code/comments — English. Product UI/content — RU + EN. Owner communicates in RU.

## §2 Active Projects / Contexts

### §2.1 OneiroScope (primary)
- Production target: Render.com (backend + frontend + Postgres + Redis blueprint).
- LLM providers (cost order): Groq (free) → Gemini ($0.075/1M) → Together → OpenAI → Anthropic.
- Default LLM env: `GROQ_API_KEY` or `GEMINI_API_KEY`. Fallback templates exist for all services.

### §2.2 Current branch
- `claude/eager-noether-5UQJR` — adding MCP server + ADK agent + skills layer.

### §2.3 Active freelance
*(none recorded — populate when relevant)*

### §2.4 KB sources
- Astrology: Swiss Ephemeris (SWIEPH binary files), `backend/services/astrology/knowledge_base/` (planets/houses/aspects JSON), `backend/data/lunar_tables.json`.
- Dreams: `backend/services/dreams/knowledge_base/symbols.json` (56 symbols, 7 modern), DreamBank Hall/Van de Castle norms `hvdc_norms.json`, prompts in `backend/services/dreams/ai/prompts/`.
- Geo: GeoNames API (username `alpro1000`, 30k req/day), 90+ city fallback DB.

## §3 Rules / Discipline

5 rules owner enforces (owner-side, NOT Claude Code's job):

1. **Pre-session:** Owner does nothing. Claude Code must read the mandatory block in `CLAUDE.md` within first 3 minutes of any session. If it doesn't — owner stops and reminds.
2. **Post-session:** Owner verifies Claude Code updated `docs/soul.md §9` (Session log). Last Gate of every task. If forgotten — owner asks: *"Update docs/soul.md §9 with this session log."*
3. **Architectural decisions** (new AI provider, DB switch, Core↔Kiosks pattern change, new MCP tool taxonomy): update `docs/steering/*.md` — usually `tech.md` or `structure.md`.
4. **New project / case / corpus:** update `§2.3` (Active freelance) or `§2.4` (KB sources) here.
5. **Project Knowledge sync (claude.ai online):** owner copies `soul.md` + `steering/*` into Project Knowledge on claude.ai weekly (or after major update). Claude Code (CLI/home) sees this via Git automatically.

**NOT discipline (skip):**
- Every commit → soul.md update: NO, only for substantial work.
- Updating tasks/specs: not mandatory if spec is finished — just archive the status header at the top.
- Versioning steering docs: only on major rewrite.

## §4 Code style / Conventions

- Backend: Pydantic v2 strict contracts, async services, no mocks in production code, fallback templates instead.
- LLM: provider abstraction via `UniversalLLMProvider`, cost-ordered selection, retry-with-fallback.
- Frontend: Server components for SSR data fetch, client components only when interactive. next-intl for all user-facing strings.
- Tests: pytest backend, jest frontend. No new feature ships without at least a smoke test.
- Commit messages: imperative ("add", "fix", "refactor"), no Claude Code session-id leak into commit body.

## §5 Known issues / Tech debt

- No user auth / natal chart persistence (TODOs in `backend/api/v1/astrology.py:59,102,175`).
- ~~5/14 dream interpreter tests failing (64% pass rate).~~ **Fixed 2026-05-26 in `claude/fix-dream-narrative-tests`** — 14/14 passing.
- ~~`ENVIRONMENT=production` not yet set on Render~~. Already set in `render.yaml` (verified 2026-05-26).
- ~~LLM cost tracking middleware structure exists but counter not wired~~. **Fixed 2026-05-26 PR #111** — `backend/core/cost_tracker.py` wired into `UniversalLLMProvider.generate()`.
- ~~Ephemeris mode (SWIEPH vs MOSEPH) not logged in `/health`~~. **Fixed 2026-05-26 PR #111** — and now also logged on app startup (PR #113).
- LunarWidget no retry on 502.
- **`build-and-validate` CI is red on every PR** (pre-existing). Diagnostic improvements landed in PR #113 (`pip install -v`, upgraded setuptools/wheel); next iteration should see the actual error trace. Not blocking — `mergeable_state` is `unstable` not `blocked`.

## §6 Architecture decisions log

See `docs/steering/tech.md` for technology choices and `docs/steering/structure.md` for layering.

Recent decisions:
- **2026-05-26** — Adopting MCP-first architecture. MCP server wraps existing FastAPI services as tools; ADK agent built on top; skills consume the agent. Rationale: reusable across Claude Desktop / Cursor / web Claude Code; one set of contracts.

## §7 Deployment notes

- Render blueprint: `render.yaml` (backend + frontend + Postgres + Redis).
- Env vars exchange via `RENDER_EXTERNAL_URL` (frontend ↔ backend).
- After updating `NEXT_PUBLIC_*` envs → **Clear build cache & Deploy** on frontend.
- LLM keys stored as Render secrets (`sync: false` in blueprint).

## §8 Open questions / Parking lot

- Should MCP server run as separate Render service or embedded in backend? → Leaning separate: cleaner cost/security boundary.
- Auth strategy for MCP HTTP transport? → JWT? OAuth? Bearer token from Render env initially.
- Cache strategy for natal charts before user-auth lands → Redis with content-hash key (birth_date+place+time).

---

## §9 Session log

### 2026-07-05 — claude/top-cities-living-work-shxind — MCP hardening, two-layer reports, second-subject field test (PRs #136–#144)

**Trigger:** continuation of the physiognomy session — owner asked to
subscribe to PR bot reviews and fix what's real, make physiognomy a
full MCP connector with file output, restructure reports (full
narrative first, then theses), and field-test the system on a second
person (friend, b. 26.03.1978 03:20 Zaporizhzhia, 18 photos).

**Done (all merged to main):**
- **Security hardening across PRs #136–#141, #143** — shared safe-path
  module `backend/mcp/tools/_files.py`: CWE-22 path confinement,
  project root from `__file__` (not cwd), writes confined to
  gitignored `reports/`, `.html`-only suffix, anchor-root exclusion
  (TMPDIR=/ case) + fallback test, photo reads confined to
  home/tmp/project, collision-proof names, 8MB + content-type cap on
  the API. Bot-review convergence policy applied: ~19 findings
  accepted/fixed, ~15 rejected with written rationale (Amazon Q went
  6+ consecutive false positives, incl. confusing the one-arg
  back-compat wrapper with the two-arg `_files` function).
- **Two-layer reports (#140):** full deterministic narrative
  (`compose_narrative`, KB text woven with connectives only, 0.6) →
  memorable theses (`compose_theses`) → sourced data → disclaimer.
  Applied to physiognomy + new MCP file-report tools
  `horoscope_report` and `profile_report_file`.
- **conventions.md §11 (#142):** external "senior engineer" prompt
  templates triaged — debugger/UI adopted; architect/review/perf
  bounded by Karpathy anti-bloat; persona simulation REJECTED in
  favor of the real adversarial loop (pytest + review bots +
  convergence policy).
- **Owner-caught contradiction → metric semantics fix (#144):**
  `lip_fullness` (inner-lip gap 13/14) measures mouth OPENNESS, not
  anatomical thickness — an expressive mouth averaged into «тонкие
  губы» across mostly-closed frames. Geometry no longer emits mouth
  readings (questionnaire-only); schema description corrected; 2
  backlog items (outer-point thickness metric; inter-frame
  variability as a first-class trait). Tests 23/23.

**Field test #2 (friend, 18 photos → 13 valid / 5 rejected by gates):**
- Earth-primary 13/13 (0.997–1.687), Water secondary 8/13; lower court
  rivals middle (two life peaks); nose borderline wealth (mean 0.2687);
  «живой рот» — lip-gap range 0.008–0.047 became the live case above.
  Chart cross-check: ASC Capricorn matches Earth face; Uranus·MC 0.2°;
  Rome crown +7.9 clean. Reports delivered (PDF + fixed HTML),
  anonymized — friend's PII excluded per repo rule.
- **ChatGPT-comparison lesson (recorded as method principle):** an
  unmeasured reader assigns elements from the presentation layer
  (smiles, poses, styling) and packages it in one confident voice;
  our split — skeletal structure (measured, 1.0) vs tradition
  dictionary (0.6) vs behavior — is exactly the provenance discipline
  that catches this failure mode. Structure ≠ подача.

**Dataset to date:** 2 people, ~39 photos, ~29 valid reads, ~8 honest
gate rejections; 6 live calibration findings, 4 closed in code.

**Deferred:** anatomical lip-thickness metric, inter-frame variability
trait, occlusion flags, dual-reference eye metric, child-face mode,
frontend `/[locale]/face`, Render build check with mediapipe/opencv.
**Next session (owner's plan):** re-run the friend's photos fresh
(«на чистую голову») end-to-end through the merged pipeline.

---

### 2026-07-04 — claude/top-cities-living-work-shxind — Physiognomy service (mianxiang + Western traditions)

**Trigger:** live client session (astrocartography consultation) drifted
into face reading; owner set goal: encode the Chinese mianxiang system +
Western physiognomy into OneiroScope with a photo-upload flow.

**Done:**
- Spec `docs/specs/physiognomy/` (requirements EARS + design + tasks).
- New service `backend/services/physiognomy/`: KB (`mianxiang.json` —
  5 elements, 3 courts, 12 palaces, 20 features; `western.json` —
  Lavater, Corman, Kretschmer, fWHR) with per-entry sources (Ma Yi Shen
  Xiang, Shen Xiang Quan Bian, Lavater 1775, Corman 1937, Kretschmer
  1921, Geniole 2015, Todorov 2017).
- Deterministic pipeline: FaceMesh 468 landmarks → scale-free ratios
  (`geometry.py`, confidence 1.0) → threshold classifier + KB lookup
  (`analyzer.py`, tradition tier **0.6** — deliberately below the 0.8
  symbol-dictionary tier because physiognomy lacks scientific validity).
- API `/api/v1/physiognomy`: GET /methods, POST /analyze
  (landmarks|metrics|features questionnaire), POST /analyze-photo
  (server CV optional → 501 with client-side guidance when mediapipe
  is absent). Privacy-first: photo stays in the browser; only landmark
  coordinates travel.
- Ethics: self-reflection only; disclaimer forbids use on third
  parties/hiring/legal; no health or attractiveness judgments.
- Tests: `backend/tests/test_physiognomy.py` — 9 passed (metric
  tolerance 1e-6, element classification, source+0.6 on every reading,
  disclaimer + forbidden-determinism words, questionnaire-only mode,
  no metric/questionnaire duplication).

**Live validation (same session, 21 photos of the owner 1981–2026):**
- 16 valid reads / 5 honest rejections; adult profile Earth-primary
  16/16, Metal secondary — reproducible across cameras and decades;
  same-day 4-photo series: fWHR spread 0.02 = method precision.
- 4 calibration findings from real photos: child-face/fringe
  (width_length off-scale), upper-court occlusion, yaw rotation,
  ICD/eye conflating aperture size with spacing (resolved with PD
  data: «55» was frame lens width 55-16, PD≈64).
- **Yaw pose-gate implemented same session** (eye-width asymmetry
  >0.20 → ValueError; 10 tests green) — rejected the rotated frame,
  passed frontals. Remaining 3 findings in tasks.md backlog.
- mediapipe==0.10.14 + opencv-headless added to backend requirements
  so `/analyze-photo` computes server-side after deploy.
- Owner profile dossier moved to gitignored `.claude/personal/
  owner_profile_patterns.md` (bot review caught the repo's own PII rule;
  full content also delivered to owner as PDFs). NOTE: the file existed
  in main history via PR #135 — history rewrite left to owner's call.
- Follow-up PR: bot-review fixes (zero-guard geometry, 8MB+content-type
  upload cap, response_model for /methods) + physiognomy MCP connector
  (`analyze_face`, `physiognomy_report` → HTML file, `physiognomy_methods`)
  + zone-structured HTML report renderer. 12 tests green; e2e smoke:
  photo → MCP tool → report file.

**Deferred:** frontend `/[locale]/face` page (browser FaceLandmarker +
questionnaire fallback), occlusion flags, dual-reference eye metric,
child-face mode, zone-structured report renderer, optional LLM
narrative layer (0.7).

---

### 2026-07-02 — claude/july-2026-transits-jja4qn — Dreams: Russian morphology + non-blank LLM fallback

**Trigger:** live walkthrough of the dreams KB found an inflected Russian
dream losing 5 of 8 symbols (exact/prefix keyword matching can't handle
case endings: «змею»≠«змея»), and `interpretation` coming back BLANK in
no-keys mode (the provider chain returns a stub with provider=None which
the parser accepted as an answer, so `_generate_fallback` never ran).

**Done:**
- `backend/services/dreams/morphology.py` — pure-Python Snowball Russian
  stemmer (no deps): normalize (ё→е), stem, keyword_stems (min length 3
  vs false positives), text_stems. «водитель» does NOT collapse to «вода».
- `analyzer.py` — stem-set pass in `_find_symbols` when regex misses;
  demo dream now yields 9 symbols instead of 3.
- `symbols.json` — suppletive verb/kin forms the stemmer can't unify
  (лечу/летел…, упал…, матери, отца…, бегу…) for 6 symbols.
- `ai/interpreter.py` — raise on provider=None / empty / unparseable LLM
  reply → existing `_generate_fallback` produces real summary +
  interpretation + recommendations instead of blank text.
- Tests: `test_dream_morphology.py` (15 cases) added to mcp-smoke; full
  smoke set now **269 passed**.

---

### 2026-07-01 — claude/july-2026-transits-jja4qn — Pattern features from live testing + synastry (Phase 9)

**Goal:** Turn the patterns from 4 live user tests (owner + 3 friends, all
Zaporizhzhia-born) into product features, plus compatibility (synastry).
Session earlier shipped interactive astrocartography (PR #130) and full
CI-green fixes incl. a real LunarWidget self-cancelling-effect bug (PR #131).

**Done (backend services, `backend/services/astrology/`):**
- `historic_tz.py` — birth-moment resolver: coordinates→IANA zone
  (timezonefinder) → zoneinfo historic rules (Soviet decree time works:
  1977/1989 Zaporizhzhia = UTC+3). Provenance: source, offset, pre-1970 flag.
  Rejects bad tz names instead of silently using UTC.
- `synastry.py` — inter-chart aspects + 5 dimension scores (attraction /
  emotional / communication / stability / tension, 0–100) + reflective
  summary. Conjunction nature resolved by planet pair (soft vs intense).
- `transit_arcs.py` — thematic phase timeline: significators derived from
  natal houses (occupants + cusp rulers + natural planets) per theme
  (money_debt / career / relationships / home); slow transits grouped into
  pressure/support phases + first sustained turning point. Reproduces the
  hand-made debt analysis (1989 chart: turning point = 2027-08).
- `astrocartography.py` — `clean` luck flag in `relocation_summary`
  (benefic angular AND no malefic angular ≤6°: Warsaw clean, Prague not);
  `compare_locations()` (side-by-side, order preserved); `theme_scan()`
  (luck/career/relationships/home city ranking with clean flags).
- `solar_return.py` — `suggest_locations()`: SR-relocation ranking by
  benefics/malefics in angular houses.
- `report.py` — one-call profile bundle (natal + places + themes + year
  transits + provenance + disclaimer) as JSON and self-contained HTML
  (print-to-PDF), no new deps.

**API (`/api/v1/astrology`):** `/astrocartography/compare`,
`/astrocartography/themes`, `/transits/arcs`, `/synastry`,
`/solar-return/suggest`, `/report` (json|html). ValueError → 400.

**MCP:** `compare_relocations`, `scan_cities_by_theme`, `transit_arc`,
`synastry`, `solar_return_suggest` registered in `server.py` (Phase 9 block).

**Tests:** +13 in `test_strategic_astro_tools.py` (28 total there) locking
session-validated facts: USSR +3h offsets, Warsaw-clean/Prague-mixed,
Pluto□Mars debt peaks (Jan+Oct 2026), synastry symmetry + bounded scores,
SR ranking, report structure incl. Sun-in-Cancer anchor. Full CI smoke set
locally: **254 passed**.

**Patterns that drove this (from live tests):** users live on their
Uranus/Pluto/Mars lines while their Venus/Moon belts are elsewhere; "clean
vs mixed" luck changes the read entirely; users ask for "строго по
транзитам" (raw-data-first); every reading converges to 4 themes
(luck/career/relationships/home); the deliverable is always the same
report bundle.

---

### 2026-06-29 — Real-use field notes + /me personal skill

Long session split in two: (1) finished the P1 queue, (2) used OneiroScope
as a real personal Strategic Analyst end-to-end, which surfaced concrete
product feedback.

**Shipped (code):**
- Earlier P1 work: `planet_in_house` (10×12), `transit_meanings`, frontend
  pricing/account/checkout (Phase 6.G), DE/ES/FR UI locales (Phase 6.F).
- `.claude/skills/me/SKILL.md` + `.claude/personal/profile.md` — a `/me`
  personal astrologer + dream interpreter. **The profile holds private data
  and is gitignored** (`.claude/personal/`, `.claude/skills/me/`) — local
  only; the public repo must not carry owner PII.

**Product conclusions (see `docs/FIELD_NOTES_real_use.md`):**
- The Strategic Analyst posture (no determinism / provenance / confidence /
  life-context-wins) is the real, if niche, differentiator. Validated.
- Gaps for the roadmap: per-angle astrocartography output (Asc/MC/IC/Desc →
  plain meaning); "score = tone, not intensity" caveat; time-sensitivity UX
  (transits robust vs angles/astrocartography sensitive ~15°/h); `.se1`
  bundling matters specifically for relocation precision; persistent saved
  chart/profile (`natal_chart_id` TODO).
- Safety: added "never interpret external clinical instruments (MMPI)" to
  `strategic_system.md`; lottery/gambling "lucky periods" stay refused.

**Note:** OneiroScope monetization left intentionally open (not decided
either way this session).

---

### 2026-06-28 (late-4) — P1 #6 (partial): DE/ES/FR UI locales (Phase 6.F)

Last item in the P1 queue. **Deliberately partial** — split the
engineering from the content-quality work, because PLAN §6.F gates the
domain content on DeepL Pro + human native review (which I cannot do
autonomously and won't fake).

**Done (engineering, shippable):**
- `frontend/messages/{de,es,fr}.json` — complete machine-draft of all 157
  UI strings. Validated programmatically: identical key shape + matching
  `{placeholders}` vs `en.json`. **Marked as pending native review.**
- `i18n/request.ts` + `middleware.ts` — locales en/ru/de/es/fr.
- `LanguageSwitcher` — DE/ES/FR buttons.
- tsc clean, next build green, jest 7/7.

**NOT done (left for the content pipeline, by design):**
- `backend/data/lunar_tables.json` + `dreams/knowledge_base/symbols.json`
  DE/ES/FR — these are the domain content needing DeepL + native review.
  Backend already falls back to EN, so de/es/fr users get localized UI
  chrome + EN domain content until the pipeline runs.

So **P1 #6 is partially closed**: UI locales live; content translation
remains a discrete follow-up (still needs a human + DeepL key).

**Shipped:** PR merged to `main`.

**P1 queue now empty of fully-autonomous items.** Remaining work is P0
(Cloud Run staging, Alembic) + the human-gated content half of #6.

---

### 2026-06-28 (late-3) — P1: frontend pricing / account / checkout (Phase 6.G)

Continued the P1 queue (goal "делай следующий незакрытый p1"). After the
two backend archetype P1s, the next unclosed item was the monetization
frontend surface (#5) on top of the existing Phase 6 Lemon Squeezy backend.

**Done:**
- `frontend/lib/auth-client.ts` — register/login/me + localStorage token
  storage (server-safe no-ops, Bearer header helper).
- `frontend/lib/billing-client.ts` — `createCheckout` (hosted Lemon URL)
  + `getSubscription`.
- Pages (bilingual RU/EN, design-token styled):
  - `[locale]/pricing/` — Free / Premium $9.99 / Pro(BYOK) $5.99 + one-time
    ($19 natal PDF, $29 yearly). Unauthed CTA → `account?next=pricing`.
  - `[locale]/account/` — login/register, profile + subscription summary,
    upgrade CTA, logout; resumes checkout via `?next`.
  - `[locale]/checkout/success/` — polls `/billing/me` for webhook-lagged
    tier activation.
  - `Header` nav + `messages/{en,ru}.json` (Pricing/Account/CheckoutSuccess).
- **Verified:** `tsc --noEmit` clean, `next build` green (all 3 routes
  compile, dynamic), `jest` 7/7.

**Prices** come from PLAN.md Phase 6 matrix. Pricing still uses placeholder
USD only in the UI; multi-currency display (€/₽) and the actual Lemon
variant IDs are env/dashboard config (`LEMON_VARIANT_*`), not frontend.

**Shipped:** PR merged to `main`.

**Still deferred:** Cloud Run staging smoke, Alembic migrations, DE/ES/FR
content translations (the last remaining P1, needs human native review).

---

### 2026-06-28 (late-2) — P1: transit_meanings archetype table

Continued through the P1 queue (goal: "делай следующий незакрытый p1").
Next unclosed item after planet_in_house was `transit_meanings.py`.

**Done:**
- `backend/services/astrology/archetypes/transit_meanings.py` — the
  transit archetype layer: symbolic meaning (conf 0.9) on top of the
  deterministic transit DATES from `compute_transits` (astronomy 1.0).
  Same composition philosophy as planet_in_house:
  - `TRANSIT_AGENDA` (6 slow transiting planets — process + tempo),
    cited to Hand *Planets in Transit* (1976) + Greene *The Outer
    Planets and Their Cycles* (1983).
  - natal drive reused from `PLANET_DRIVES`; aspect nature from `ASPECTS`.
  - `NAMED_TRANSITS` — canonical life-cycle transits get explicit
    archetype + specific citation. **Saturn □/☍ Sun = "Midlife
    reappraisal"** (the example named in next-session.md), Saturn Return,
    Pluto/Neptune/Uranus □ Sun.
  - Natal bodies restricted to Sun..Saturn to match `transits_engine`.
- MCP tool `transit_meaning()` → **MCP tools 24 → 25**; in
  `list_archetype_topics`.
- Tests +7. **Backend suite: 275 passed, 6 skipped.**

**Shipped:** PR merged to `main`.

**Still deferred (unchanged):** Cloud Run staging smoke, Alembic
migrations, frontend pricing/checkout, DE/ES/FR content translations.

---

### 2026-06-28 (late) — P1: planet_in_house hard table (10×12)

Follow-up session after the Phase 7-9 consolidation. Picked up the
first deferred P1 item from the consolidated entry below.

**Done:**
- `backend/services/astrology/archetypes/planet_in_house.py` — the
  10 planets × 12 houses lookup, completing the Phase 8 hard-archetype
  set. Built by **composition, not fabrication**: each cell joins a
  cited planet-drive descriptor (Tompkins *Contemporary Astrologer's
  Handbook* ch.4 / Hand *Horoscope Symbols*) with the already-cited
  house life-area (Sasportas *The Twelve Houses*). We deliberately do
  NOT invent a distinct page citation per cell — both real sources are
  returned joined, keeping the provenance principle honest.
- MCP tool `planet_in_house()` (layer `astrology_symbolic`, conf 0.9,
  disclaimer); registered in `server.py` → **MCP tools 23 → 24**.
- Listed in `list_archetype_topics`.
- Tests +5 (full 10×12 grid, dual-citation assertion, case-insens,
  invalid-input, tool wrapper). **Backend suite: 268 passed, 6 skipped.**

**Birth-chart verification run** (01.07.1977 22:30 Запорожье, UTC+3 —
re-confirmed via IANA `Europe/Zaporozhye` = +3 for that date, decree
time, no pre-1981 DST): full path planets → house assignment → table
produced cited deterministic readings for all 10 planets. Two honest
caveats on *that run* (not the code, which is test-covered): this
container lacks `.se1` files → MOSEPH approximate positions; house
numbers derive from an approximate Asc (~16° Aquarius) so are
indicative, not arc-precise. In prod (ephemeris files + GeoNames) the
placement is exact.

**Shipped:** PR merged to `main` (branch `claude/phase-9-consolidation-f64chg`).

**Still deferred (unchanged):** Cloud Run staging smoke, Alembic
migrations, `transit_meanings.py`, frontend pricing/checkout, DE/ES/FR
content translations.

---

### 📌 2026-06-28 — SESSION CONSOLIDATED (Phases 7-9 landed today)

End-of-day consolidation. Three merged PRs this session:

| PR | Phase | What |
|---|---|---|
| **#121** | 7 | Strategic Life Cycle Analyst pivot — 8-layer evidence matrix, no-determinism validator, 3 deterministic astronomy MCP tools (compute_transits, astrocartography_scan, solar_return_chart), Strategic Analyst agent, rewritten system prompts |
| **#122** | 8 | Hard archetype tables (MC/Sun/Houses/Aspects/Dignities with cited classical sources), 7 new MCP tools, Cloud Run + Vertex AI guide with ADC auto-detect, domain.md + conventions.md from peer-review scaffold, numeric confidence ladder, disclaimer enforcement |
| **#123** | 9 | Memory system harmonization — next-session.md, _TEMPLATE_spec/, _TEMPLATE_bug/, English TL;DR blocks in steering docs, §10 «Rejected ideas» |

**Numerical state at end-of-day:**
- MCP tools: **23** (was 13 at start of day)
- Specialist agents: **4** + 1 orchestrator
- Backend test suite: **263 passed, 6 skipped** (was 183)
- Memory scaffold files: **complete** (CLAUDE.md + soul.md §1-§10 + steering/5 files + next-session.md + 7 templates)

**Major architectural shift this session:** OneiroScope is no longer "another AI horoscope". It is now positioned as **Strategic Life Cycle Analyst** with:
- Provenance per claim (every output cites which layer + source)
- Confidence ladder 1.0/0.9/0.8/0.7 (astronomy / cited tradition / symbol dict / LLM)
- No deterministic prediction language (regex-validated)
- Mandatory disclaimer (5 locales, enforced)
- Hard archetype tables as 0.9-confidence layer (above LLM 0.7) for the well-known archetypal interpretation surface

**Key correction surfaced this session:** Prior manual chart analyses used wrong timezone (UTC+4 vs correct UTC+3 for USSR summer 1977 — decree time, no DST until 1981). All new MCP tools use `zoneinfo` correctly. The famous Jupiter ☌ natal Saturn aspect for the test chart (01.07.1977 22:30 Запорожье) is actually **September 11, 2026**, not August 25 — falls in the first 2 weeks of the user's magistratura at Pardubice.

**What's deferred to next session (P0/P1 in `docs/next-session.md`):**
- End-to-end smoke on Cloud Run staging
- Alembic migrations for User/Subscription/UserLLMKey
- `planet_in_house.py` (10 × 12 archetype table, completes Phase 8 set)
- `transit_meanings.py` (transit archetype with citations)
- Frontend pricing/checkout/account pages (Phase 6.G)
- DE/ES/FR translations for lunar_tables / symbols (human native review)

**Next session start sequence:** follow `CLAUDE.md` mandatory block — read 8 files in order (conventions → product → tech → structure → domain → soul → PLAN → next-session). The `next-session.md` file lists exact P0/P1/P2 priorities.

Individual phase entries below (chronological within today).

---

### 2026-06-28 — claude/memory-system-harmonization — Phase 9: scaffold memory-system harmonization

**Goal:** Owner shared the peer-review scaffold from another chat (full STAVAGENT-style memory-management system). Apply the missing pieces here: `next-session.md` handoff format, `docs/templates/_TEMPLATE_{spec,bug}/` workflows, English TL;DR blocks in steering docs, §10 "Rejected ideas" in soul.md, cleaner CLAUDE.md mandatory block.

**Done:**
- `docs/next-session.md` — handoff snapshot with project state table, what works / what's broken, P0/P1/P2 priorities, "context easy to lose" notes (USSR 1977 = UTC+3 not UTC+4, Jupiter ☌ Saturn = Sep 11 not Aug 25, etc.), open architectural decisions.
- `docs/templates/_TEMPLATE_spec/{requirements,design,tasks}.md` — full SDD template trio. EARS-style criteria, provenance-ladder mapping, 6 implementation Gates.
- `docs/templates/_TEMPLATE_bug/{report,analyze,fix,verify}.md` — reproduce-first bug workflow. Hypothesis-generation in analyze.md, domain-rule re-check in verify.md.
- `CLAUDE.md` mandatory block — expanded to read 8 files in order (conventions → product → tech → structure → domain → soul → PLAN → next-session). Added English TL;DR for external readers + the 5 core principles spelled out.
- `docs/soul.md` — English TL;DR + section map at top; new §10 «Rejected ideas» with 6 entries (Stripe+YooKassa, Llama-as-primary, Co-Star positioning, MCP separate service, pure-LLM MC interpretation, Chiron MOSEPH).
- `docs/steering/{product,tech,structure}.md` — added English TL;DR blocks in headers.
- `docs/PLAN.md` — Phase 8 logged + Phase 9 added and checked off.

**Decisions:**
- Kept `docs/steering/conventions.md` and `domain.md` from Phase 8 untouched (already match the scaffold).
- Did NOT renumber soul.md sections (would break all earlier §-references in commit history). Added §10 instead of fitting "Rejected ideas" into existing slots.
- Did NOT add `docs/specs/` or `docs/bugs/` directories yet — templates are ready to copy when needed, but creating empty dirs is bloat.

**Verification:**
- All scaffold-required files present: CLAUDE.md ✓, soul.md (§1-§10) ✓, steering/{product,tech,structure,domain,conventions}.md ✓, next-session.md ✓, templates/_TEMPLATE_{spec,bug}/ ✓.
- No code change in this PR → no test impact.

---

### 2026-06-28 — claude/hard-archetypes-cloudrun — Phase 8: Hard archetype tables + Cloud Run + scaffold adoption

**Goal:** After Phase 7 Strategic Analyst pivot, user requested **hard interpretation modules** (MC archetype tables, Sun, Houses, Aspects, Dignities) — so the system can cite classical/modern sources directly without going through LLM_NARRATIVE (0.7) → upgrade to ASTROLOGY_SYMBOLIC (0.9) with provenance. Also: peer-review scaffold suggestions to adopt + Cloud Run / Vertex AI integration.

**Done — archetype tables (`backend/services/astrology/archetypes/`):**
- `zodiac_signs.py` — 12 signs × {element, modality, ruler, keywords, shadow, description, source}.
- `mc_in_sign.py` — 12 MC archetypes (career role, NOT "destiny").
- `sun_in_sign.py` — 12 Sun archetypes (identity, with growth_edge).
- `houses.py` — 12 houses × area-of-life with natural sign/ruler.
- `aspects.py` — 5 aspects (conjunction/opposition/trine/square/sextile) with default orbs from domain.md §2.3.
- `dignities.py` — essential dignity table (domicile/exaltation/detriment/fall/peregrine) using **traditional** rulers per Lilly 1647.
- All citations from Sue Tompkins, Liz Greene, Howard Sasportas, Robert Hand, Stephen Arroyo — real, well-cited modern astrology sources.

**Done — MCP tools (`backend/mcp/tools/archetypes.py`):**
- 7 new tools: `mc_in_sign`, `sun_in_sign`, `house_meaning`, `aspect_meaning`, `planet_dignity`, `zodiac_sign`, `list_archetype_topics`.
- Each returns `{layer: "astrology_symbolic", confidence: 0.9, ..., source: <citation>, disclaimer: <text>}`.
- Registered in `backend/mcp/server.py` (total 23 tools, was 16).
- Added to `StrategicAnalystAgent.allowed_tools` (now 19, was 12).

**Done — scaffold adoption:**
- `docs/steering/domain.md` — adopted from scaffold. Confidence ladder 1.0/0.9/0.8/0.7, disclaimer rules, forbidden patterns, acceptance criteria (provenance/disclaimer/tolerance, not exact text).
- `docs/steering/conventions.md` — Karpathy anti-bloat rules, EARS-style criteria, commit/branch naming, update matrix, gates.
- `backend/services/strategic/disclaimer.py` — `ensure_disclaimer(text, locale)`, `has_disclaimer()`, sentinel-phrase paraphrase detection. 5-locale canonical text (RU/EN/DE/ES/FR).
- `backend/services/strategic/layers.py` — added `numeric_confidence()` function, `LAYER_CONFIDENCE` table mapping Layer → 0-1 numeric, convergence bonus.

**Done — Cloud Run + Vertex AI:**
- `docs/deployment/CLOUD_RUN.md` — full step-by-step (project setup → service account → secrets → Cloud SQL → Cloud Build → deploy → custom domain → optional Swiss Ephemeris bucket → CI/CD via Cloud Build trigger). ~$10-21/mo at MVP traffic.
- `backend/core/llm_provider.py::_provider_configured(VERTEX)` — now detects Cloud Run via `K_SERVICE` / `K_REVISION` env vars (set by Cloud Run automatically). When present + `VERTEX_PROJECT`, Vertex activates via metadata-server ADC — no explicit token needed.

**Tests:**
- `test_archetypes.py` — 35 tests (table completeness, required fields, dignity calculations, MCP tool wrappers carry layer/confidence/disclaimer).
- `test_disclaimer_and_numeric_confidence.py` — 18 tests (disclaimer detection across locales, paraphrase tolerance, idempotency; numeric ladder values match scaffold, convergence bonus, LLM-only cap).
- Updated `test_mcp_smoke.py` registry to include 7 new archetype tools.
- Updated `test_strategic_agent.py` allowed-tools to include archetype tools.
- All added to `mcp-smoke.yml` CI.
- Full backend suite: **263 passed, 6 skipped** (was 183 → +80).

**Decisions:**
- Archetype tables are deterministic Python dicts with cited sources — not configurable, not LLM-generated. This is the "0.9 cited classical rule" tier from the scaffold confidence ladder.
- Disclaimer is **enforced at the response layer** via `ensure_disclaimer()` — auto-appends if LLM forgot. Sentinel-phrase detection lets the LLM phrase its own version.
- Numeric confidence is **derived** from source mix, not declared. The 3-bucket Confidence enum (HIGH/MEDIUM/LOW) still exists as UI labels; the 0-1 float is for fine-grained ranking.
- Cloud Run vs Render: Cloud Run wins for solo founder (scale-to-zero, ~$10/mo vs ~$21/mo). Vertex AI ADC via metadata-server is the right path — no secrets to rotate.

---

### 2026-06-14 — claude/strategic-analyst-pivot

### 2026-06-14 — claude/strategic-analyst-pivot — Phase 7: Strategic Life Cycle Analyst pivot

**Goal:** After a long product-direction conversation (user explored own chart deeply with the existing tools, then surfaced peer-review feedback that "another astrology AI" is the wrong positioning), execute the **Strategic Life Cycle Analyst pivot** end-to-end in one PR: multi-layer evidence-matrix substrate, new deterministic astronomy tools (transits, astrocartography, solar return), new Strategic Analyst agent, rewritten domain prompts to inherit the posture.

**Why this matters now:** Co-Star / Sanctuary / Nebula saturate the predictive-astrology market with unfalsifiable text. OneiroScope's defensive moat is **forced source-attribution** — every claim is tagged with which analytical layer (astronomy / age psychology / user context / symbolism) produced it, and confidence is derived from the source mix, not declared. Astrology stays as a symbolic layer; it just doesn't get to pretend to predict.

**Done — Phase 7.A (substrate):**
- `backend/services/strategic/layers.py` — `Layer` enum (8 epistemic levels), `Source`, `Insight` (Pydantic with no-determinism validator), `EvidenceMatrix` with auto-derived `Confidence`.
- `backend/services/strategic/no_determinism.py` — regex guard for "will/будет/случится" + hedge-prefix allowlist + softener helper.

**Done — Phase 7.B (deterministic astronomy):**
- `backend/services/astrology/astrocartography.py` — `relocate()` + `scan_cities()` with planet/angle hits and a benefic/malefic scoring.
- `backend/services/astrology/transits_engine.py` — `find_transits()` with local-minimum detection over a date window.
- `backend/services/astrology/solar_return.py` — `solar_return()` with 2-stage (hourly + minute) search to arc-minute precision.
- `backend/mcp/tools/strategic_astro.py` — three MCP wrappers (`compute_transits`, `astrocartography_scan`, `solar_return_chart`), registered in `backend/mcp/server.py`. Total tools now 16 (was 13).

**Done — Phase 7.C (agent + prompts):**
- `agents/prompts/strategic_system.md` — full Strategic Analyst posture: 8 layers, hard rules (no determinism, source attribution, confidence derivation, skeptical default), required response structure (8 sections ending with Evidence Matrix), fixed closing line.
- `agents/prompts/astrology_system.md` — rewritten to inherit the posture.
- `agents/prompts/dream_system.md` — rewritten ("no diagnosis", "reflection prompts" instead of interpretations).
- `agents/specialists/strategic_agent.py` — `StrategicAnalystAgent` with 12 tools (synthesis across domains).
- `agents/orchestrator.py` — `strategic` intent router (RU + EN keywords); strategic wins when both strategic + domain present.

**Done — Phase 7.D (docs):**
- `docs/STRATEGIC_ANALYST.md` — design rationale, architecture diagram, code map, market positioning matrix, "what this is NOT", how to extend.
- `docs/PLAN.md` — Phase 7 fully checked off.

**Important correction surfaced during session:**
While running real chart tests through the new tools, discovered my prior manual analyses used **wrong timezone** (UTC+4 instead of correct UTC+3 for USSR 1977 summer — decree time, no DST until 1981). This shifted natal Asc/MC interpretations and the Jupiter ☌ Saturn date (was claiming Aug 25; actually Sep 11). The Strategic Analyst MCP tools use `zoneinfo` which handles historical timezones correctly. New tests lock in correct values.

**Verification:** 
- Backend suite: **183 passed, 6 skipped** (was 139). +44 new tests.
- All new files added to `mcp-smoke.yml` CI.
- MCP server registers 16 tools cleanly.

**Decisions:**
- Pivoted from "yet another astro AI" to Strategic Life Cycle Analyst. Free tier keeps classic astrology UI; Premium tier ($25-50/mo) gets the Evidence Matrix experience.
- Astrology kept as `Layer.ASTROLOGY_SYMBOLIC` (LOW confidence by default) — not removed.
- `Layer` enum is extensible — adding Vedic, Chinese cycles, biorhythms is "add to enum + add MCP tool".

---

### 2026-06-14 — claude/phase-6-lemon-implementation — Phase 6 production-ready: Lemon Squeezy MoR + auth + BYOK + quotas + 5-locale email + deployment & mobile guides
**Goal:** Owner is solo founder in EU, no юр.лицо. Pivot from Stripe+YooKassa to **Lemon Squeezy as Merchant of Record** and ship a production-ready service: auth, subscription, BYOK, quotas, 5-locale email scaffolding, deployment guide for Render+Vercel+Lemon+Resend, mobile strategy via Capacitor (iOS+Android).

**Plan pivot (PLAN.md Phase 6 rewritten):**
- Lemon Squeezy as MoR — handles VAT/sales tax/KYC/chargebacks; works with RU cards via card processor; **no юр.лицо**.
- 5 currencies/locales: USD/EUR + auto-detect by geo-IP; Lemon converts.
- Mobile = Capacitor wrap (Phase 6.J added) — one Next.js codebase, two app stores.
- Open questions resolved: Resend for email, DeepL Pro + human review for translations, 1 free natal lifetime + 1 horoscope/day.

**Backend implemented (production-grade):**
- `backend/models/user.py` extended: `password_hash`, `name`, `lemon_customer_id`, `free_natal_used`, `pending_deletion_at`, `llm_keys` relationship.
- `backend/models/user_llm_key.py` — new model for BYOK Fernet-encrypted keys.
- `backend/models/subscription.py` — added `tier`, `provider`, `lemon_subscription_id`, `lemon_variant_id`, `lemon_customer_id`; dropped old `check_one_gateway` constraint.
- `backend/services/byok/keys.py` — Fernet encryption derived from SECRET_KEY (rotation invalidates all keys — by design). `encrypt`/`decrypt`/`hint`.
- `backend/services/billing/quotas.py` — `Tier` enum + `assert_quota(user, QuotaKind)` raising HTTP 402 with CTA. Daily horoscope counter (in-memory; Redis path documented).
- `backend/services/billing/lemon_provider.py` — Checkout API (httpx), webhook HMAC-SHA256 signature verification, `parse_webhook()`, `tier_for_variant()`, product-slug-to-variant env mapping.
- `backend/services/email/resend_provider.py` — quiet no-op when `RESEND_API_KEY` unset; locale-aware template rendering with English fallback.
- `backend/api/v1/auth.py` — POST `/register`, `/login`, `/refresh`, GET `/me`; constant-time-ish password verification.
- `backend/api/v1/billing.py` — POST `/checkout`, `/webhook` (signature-verified + idempotent), GET `/me`.
- `backend/api/v1/users.py` — `/me/llm-keys` save/list/delete, `/me/data-export` (GDPR Article 20), DELETE `/me` (Article 17 soft-delete).
- All routers mounted in `backend/app/main.py`.
- MCP tool docstrings annotated `# ru | en | de | es | fr`.

**Email templates (5 locales):** `welcome.{subject,html}` for en/ru/de/es/fr (DE/ES/FR machine-translated baseline — flagged for native review in PLAN.md).

**Tests (38 new, all green):**
- `test_byok.py` (6): round-trip, empty rejection, tamper detection, hint redaction, secret-rotation invalidation.
- `test_quotas.py` (13): tier resolution (free/premium/pro precedence, inactive ignored), lifetime flags, daily counters, lunar always free, 402 payload shape.
- `test_lemon_provider.py` (12): signature verify (valid/tampered/missing/no-secret), variant lookup (known/unknown/unset env), tier mapping, webhook parsing (full/minimal), key/store unset errors.
- `test_email_templates.py` (7): rendering each of 5 locales, fallback to en, full variable substitution.
- Full backend suite: **139 passed, 6 skipped** (was 101 → +38).
- All 4 new test files added to `mcp-smoke.yml` CI; `cryptography` and `email-validator` added to CI deps.

**Documentation (production-ready):**
- `docs/DEPLOYMENT.md` — step-by-step Render+Vercel+Lemon+Resend setup, all env vars enumerated, custom domain DNS, monthly cost breakdown (~$65/mo), recurring ops checklist.
- `docs/MOBILE.md` — Capacitor wrap strategy, why-not-RN matrix, Xcode/Android Studio walkthrough, RevenueCat path for IAP, App Store metadata in 5 locales, 5-day timeline to TestFlight + Closed Track.
- `.env.example` extended with all Lemon Squeezy + Resend vars.

**What is NOT in this PR (tracked for next iteration):**
- Alembic migration for new User/Subscription columns — needs to be generated against existing schema (out of scope for code-only change; documented in DEPLOYMENT.md §1.3 as a one-time bootstrap step).
- Quota wiring into astrology/dreams endpoints (Phase 6.B sub-item) — service exists, the `Depends()` call to plug it in is straightforward but touches every endpoint signature; safer as a focused follow-up PR.
- DE/ES/FR translation of `lunar_tables.json` (31 days) and `symbols.json` (56 entries) — needs human native review with astrology/psychology context; flagged in DEPLOYMENT and PLAN.
- Frontend pricing/account/login pages — frontend work is the owner's plan.
- Capacitor `mobile/` directory — depends on `next.config.js` static-export flip; documented in MOBILE.md as the owner's next step.

---

### 2026-05-31 — claude/plan-phase-6-monetization — Phase 6 plan: monetization + 5-language GA
**Goal:** After owner clarified product direction (hybrid BYOK+web, audience RU/EN/DE/ES/FR), write Phase 6 of the plan covering auth, subscription, payments, and i18n expansion. No code yet — planning only.

**Decisions captured (from chat):**
- Backend ASR (Whisper/Vosk) **stays** — owner will build the web frontend; voice input is a UX driver for mobile.
- Audience: **5 languages** (RU, EN, DE, ES, FR) on the web, simultaneously.
- Two access paths: **MCP free (BYOK)** as community/SEO loss-leader + **Web subscription** for non-tech users.
- Pricing tiers drafted: Free / Premium ($9/€9/799₽) / Pro-BYOK ($5/€5/499₽) / one-time reports ($19-29).

**Phase 6 sub-phases written into `docs/PLAN.md`:**
- 6.A Auth foundation (JWT, User model, email verification).
- 6.B Subscription & quota DB, quota enforcement on astrology/dreams endpoints.
- 6.C Stripe integration (intl: USD/EUR markets).
- 6.D YooKassa integration (RU market; flagged юр.лицо requirement).
- 6.E Pro/BYOK tier — per-user encrypted LLM key + provider override.
- 6.F i18n DE/ES/FR — frontend messages, backend prompts, `lunar_tables.json` keys, dream-symbols translations, MCP `locale` enum extension, language auto-detect.
- 6.G Frontend pricing + checkout + account pages (region-aware provider routing).
- 6.H Transactional email (Resend/SendGrid, multilingual templates).
- 6.I GDPR compliance (data export, delete, cookie banner, privacy policy, retention).

**5 open questions documented at end of Phase 6** — owner needs to answer before implementation: юр.лицо для YooKassa, страна Stripe-аккаунта, email-провайдер, переводчик (DeepL vs human), free-tier лимиты.

---

### 2026-05-31 — claude/orchestrator-error-handling — gather(return_exceptions=True) fix
**Goal:** Address Amazon Q's review of PR #117 — multi-domain `asyncio.gather` would crash on any specialist failure.

**Done (PR #118):** `return_exceptions=True` + per-result `BaseException` check; failed domains surface as tagged inline `## Dream — temporarily unavailable: RuntimeError` block. Regression test `test_multi_domain_partial_results_when_one_specialist_crashes`. Suite: 101 passed, 6 skipped.

---

### 2026-05-31 — claude/adk-orchestrator — ADK Phase C+D: SuperOrchestrator + cost-tracker agent tag
**Goal:** Complete the SuperOrchestrator (routing + fan-out + merge) and per-agent cost tracking, finishing the plan started in PR #116.

**Done — Phase C (orchestrator):**
- `agents/orchestrator.py` — `SuperOrchestrator` with keyword-based intent router (deterministic, no extra LLM call). Single-domain passes streaming through as-is; multi-domain runs specialists in parallel via `asyncio.gather` and merges output with `## Domain` headers. Specialists are instantiated lazily — no idle stdio MCP children.
- `agents/cli.py` — `SuperOrchestrator` is now default; `--generalist` opts into the old single-agent path.
- Keyword tuning: `гороск` not `горо` (the latter false-matched "город" → mis-routed dreams about cities to astrology).

**Done — Phase D (cost-tracker agent tag):**
- `backend/core/cost_tracker.py` — keys now include `<agent>` segment (`oneiro:cost:<provider>:<agent>:<YYYY-MM-DD>:<suffix>`). `record()` resolves the tag from explicit arg → `ONEIRO_AGENT_NAME` env → `"default"`. `report()` aggregates across all tags by default; `agent=` filters to one; `group_by_agent=True` returns per-agent breakdown.
- `BaseOneiroAgent` — propagates `ONEIRO_AGENT_NAME=self.name` into the spawned MCP child's env, crossing the process boundary without extra infrastructure. The backend's LLM provider reads that env transparently.

**Deferred (tracked):**
- Context passing between specialists (e.g. natal chart `chart_id` → DreamAgent for personalized interpretation). Needs the persistence layer (§5 known issue).

**Tests:**
- `backend/tests/test_orchestrator.py` — 22 tests: 13 router cases + fallback, single/multi-domain dispatch, isolation, lazy instantiation, cost-tracker tag via env, explicit-agent precedence, MCP-env propagation.
- Full backend suite: **100 passed, 6 skipped** (was 78 → +22 orchestrator/cost-tag tests).
- Orchestrator tests added to `mcp-smoke.yml`.

---

### 2026-05-28 — claude/adk-specialists — ADK Phase A+B: base class + 3 specialist agents
**Goal:** Refactor the single `OneiroAgent` into a base class and stand up 3 domain-specialist agents (Astrology / Dream / Lunar) as Phase A+B of the SuperOrchestrator plan in `docs/PLAN.md`.

**Done:**
- `agents/base.py` — `BaseOneiroAgent` (name, system-prompt path, allowed_tools subset). Shared `run()` (streaming text deltas). Idempotent `_qualify()` (bare `tool` or `mcp__oneiro__tool` both work).
- `agents/oneiro_agent.py` — `OneiroAgent` is now a 30-line subclass of `BaseOneiroAgent` keeping all 13 tools; backward-compat CLI unaffected.
- `agents/specialists/{astrology,dream,lunar}_agent.py` — each declares a narrow tool subset:
  - astrology: 7 (natal/horoscope/forecast/list_* + geo helpers)
  - dream: 4 (analyze + list_*)
  - lunar: 2 (get_lunar_day/period)
- `agents/prompts/{astrology,dream,lunar}_system.md` — domain prompts (science-first, provenance shown, no prediction-as-fact, no esoteric/forbidden content).
- `backend/tests/test_specialist_agents.py` — 10 tests: import, tool-subset correctness, prompt content, name uniqueness, qualifier idempotence, generalist backward-compat. All green.
- Full backend suite: **78 passed, 6 skipped** (was 68 + 10 specialist). Specialist tests added to `mcp-smoke.yml`.
- `docs/PLAN.md` — Phase 5 added; A+B checked off.

**Next (Phase C+D, separate PR):** SuperOrchestrator (intent router + fan-out + context-passing + merge) + cost-tracker agent tag.

---

### 2026-05-28 — claude/cloud-llm-providers — Vertex AI + Bedrock providers, horoscope/dream test run, lunar-table path fix
**Goal:** Run sample daily/monthly/yearly horoscopes + a dream for birth data (01.07.1977 22:30 Запорожье), and add Vertex AI / Bedrock as LLM providers.

**Done:**
- **Vertex AI provider** (`backend/core/llm_provider.py`): Gemini via GCP regional endpoint. Auth via `VERTEX_ACCESS_TOKEN` or ADC (`google-auth`). Gated on `VERTEX_PROJECT` + creds.
- **Bedrock provider**: Claude via AWS `bedrock-runtime.invoke_model` (boto3, SigV4, sync call in executor). Gated on AWS creds + boto3 importable. Anthropic Messages schema + `anthropic_version: bedrock-2023-05-31`.
- Both added to the cost-ordered catalog (Vertex after Gemini, Bedrock after Anthropic) and to `_provider_configured()`; disable gracefully when unconfigured.
- `backend/tests/test_llm_providers_cloud.py` — 8 tests (gating + request construction with mocked httpx/boto3). Full backend suite 68 passed, 6 skipped.
- **Bug fix**: `backend/services/astrology/interpreter.py` loaded `lunar_tables.json` from `backend/services/data/` (wrong) instead of `backend/data/` — degraded ALL horoscope template content. Fixed the path (one more `dirname`).
- Deps: added optional `google-auth>=2.27`, `boto3>=1.34` to `backend/requirements.txt`.
- Docs: CLAUDE.md env section + provider table, `docs/steering/tech.md` provider list.

**Test run results (template fallback, no LLM keys in this env):**
- Natal chart 01.07.1977 22:30 Запорожье → Sun Cancer 9.83°, Moon Capricorn, Asc Aquarius, MC Sagittarius (MOSEPH analytic — no SWIEPH binaries locally). Geocoded via 90-city fallback (47.84, 35.20, Europe/Kyiv).
- Daily/monthly/yearly horoscopes: correct period boundaries; content brief+identical because template fallback only uses lunar day (LLM keys produce 600-1000 words/period).
- Dream analysis: symbols escape_liberation/house/animal, emotion happiness 0.65, archetypes liberation/self/instinct. Interpretation empty without LLM key.

**Notes:**
- Local env briefly had the `external/pyswisseph` stub shadowing real pyswisseph (from the build-CI work) — reinstalled real `pyswisseph==2.10.3.2` for accurate positions.
- Geocoder rejects "City, Country" suffix (", Украина" failed; bare "Запорожье" works). Candidate future fix: strip country segment before fallback lookup.

---

### 2026-05-26 — claude/fix-build-ci — Build CI hardening + startup ephemeris log
**Goal:** Get `build-and-validate` CI green (red on every PR since pre-existing) + add operator-friendly startup logs.

**Done (merged via PR #113):**
- `requirements.txt` / `etl/requirements.txt`: pin `numpy>=1.26,<3`, `pandas>=2.2,<3`, `pyarrow>=15`. Clean-venv install verified locally.
- `.github/workflows/build.yml`: upgrade `setuptools wheel build` alongside pip, switch to `pip install -v` (diagnostic), use `python -m pytest` for consistency with smoke workflow.
- `backend/app/main.py`: log ephemeris mode at startup (mirrors `/health`). INFO for SWIEPH, WARNING for MOSEPH fallback with `SE_EPHE_PATH` hint.

**Outcome:** `build-and-validate` **still red on PR #113** — root cause not visible without GHA log access. Verbose flag will surface the actual error on the next iteration. Smoke + inventory + dream tests all green.

**Decisions:**
- Did not chase further without log visibility. Pinned-version + diagnostic improvements are useful regardless of whether they fully resolve build-and-validate.
- Did NOT revert changes — all three are independently beneficial.

---

### 2026-05-26 — claude/fix-dream-narrative-tests — Dream interpreter v2.1 test fixes
**Goal:** Resolve the 6 known-failing tests in `test_dream_interpreter_narrative.py::TestContextualSymbolValidation` (noted as `§5` known issue; tracked as out-of-scope in the previous session).

**Done:**
- Added Russian keyword roots to `symbols.json` for `vehicle` (`автомобил`, `авто`, `машин`), `surveillance` (`слеж`, `следи`, `наблюд`), `boundaries` (`границ`, `наруш`, `вторг`), `escape_liberation` (`выброс`, `отброс`, `свобод`, `освобод`, `облегчен`). Root: the inflection-aware regex needs a literal prefix of the surface form.
- Restored strict reinforcement requirement for `surveillance` only — lone keywords like "camera" produced false positives. Other reinforcement-driven symbols stay soft.
- Added house exclusion for `(throw|выбросил…) … (window|окн)` — common in surveillance/escape dreams, the window is not a house symbol.

**Verified:** 14/14 dream narrative tests pass; full backend suite 60/60 (6 skipped). Updates §5 (5/14 → 0/14 failing).

**Decisions:**
- Did NOT change the Russian regex compilation (still `\bkeyword\w*\b`). Keyword roots were the lowest-risk fix.
- Strict reinforcement applied only to `surveillance`; widening it to others would regress legit detection cases.

---

### 2026-05-26 — claude/eager-noether-5UQJR — MCP + ADK + Skills foundation
**Goal:** Stand up MCP-server / ADK-agent / skills layer on top of existing FastAPI services + introduce discipline files (soul.md, steering/*, mandatory block in CLAUDE.md).

**Plan reference:** `docs/PLAN.md` (phases 0–4).

**Phase 0 completed:** Created `docs/PLAN.md`, `docs/soul.md` (this file), `docs/steering/{tech,structure,product}.md`, mandatory-block header in `CLAUDE.md`.

**Phase 1 completed — MCP server (`backend/mcp/`):**
- `server.py` runs FastMCP on stdio (default) or streamable-HTTP. 13 tools registered:
  astrology (calculate_natal_chart, generate_horoscope, forecast_event, list_event_types, list_horoscope_periods),
  dreams (analyze_dream, list_dream_symbols, list_archetypes, list_hvdc_categories),
  lunar (get_lunar_day, get_lunar_period),
  geo (search_city, validate_birth_data).
- `backend/tests/test_mcp_smoke.py` — 9 tests, all green.

**Phase 2 completed — ADK agent (`agents/`):**
- `OneiroAgent` spawns MCP server as stdio child; restricts allowed_tools to `mcp__oneiro__*` (no shell, no fs).
- System prompt enforces science-first, cost-aware tool chain, bilingual parity, provenance, no prediction-as-fact.
- `python -m agents.cli "<prompt>"` CLI entry.
- 5 agent smoke tests, all green.

**Phase 3 completed — Skills (`.claude/skills/`):**
- 8 SKILL.md files: `/natal`, `/horoscope`, `/dream`, `/lunar`, `/deploy-cycle`, `/validate-prod`, `/cost-report`, `/research-symbol`.
- README lists conventions; all skills consume `mcp__oneiro__*` only.
- Expanded `.claude/settings.local.json` with common dev permissions.

**Phase 4 partial:**
- `ENVIRONMENT=production` already set in `render.yaml` (verified).
- `/health` now returns `ephemeris` block (engine + path + first 5 files).
- `mcp[cli]>=1.2` + `claude-agent-sdk>=0.2` added to `backend/requirements.txt`.
- `.github/workflows/mcp-smoke.yml` runs 14 smoke tests on push/PR.
- Deferred: `cost_tracker.py` (needs middleware wiring), separate Render MCP service (embedded works), MCP Dockerfile (backend Dockerfile covers).

**Decisions:**
- MCP-first adopted: FastAPI services strict-typed → trivial adapters; one MCP server reusable from Claude Desktop, Cursor, agents, web Code.
- Agent restricted to MCP tools only — never invokes Bash/Write/Read directly, keeps domain scope clean.
- Skill layer never calls FastAPI HTTP — only MCP tools (rule in `docs/steering/structure.md`).
- Cost tracking deferred to next session: requires deeper LLM-provider middleware change.

**Out of scope this session:** user auth, natal-chart DB persistence, 5/14 failing dream interpreter tests, separate Render MCP service.

**Verified:** 14/14 smoke tests green (`pytest backend/tests/test_mcp_smoke.py backend/tests/test_agent_smoke.py`).

*(append new entries above this line on next session)*

---

## §10 Rejected ideas (and why)

Track ideas we explicitly decided NOT to pursue, with the rationale.
Prevents re-debating the same questions in future sessions.

- **Stripe + YooKassa as payment providers** — rejected 2026-06-14
  (Phase 6 pivot). Solo founder in EU, no юр.лицо; Lemon Squeezy as
  Merchant of Record handles VAT/sales tax/KYC/chargebacks instead.
- **Llama-3.1-8b (Groq) as primary LLM for premium tier** — rejected
  2026-06-28. Llama-8b breaks the Strategic Analyst 8-section response
  structure and the no-determinism rule under load. Kept as fallback
  for free tier; premium uses Claude Sonnet 4.6 / Gemini Flash.
- **Loud public "AI horoscope" positioning (Co-Star clone)** —
  rejected 2026-06-14 (Phase 7 pivot). Saturated market with
  unfalsifiable text; OneiroScope's defensive moat is forced
  source attribution via the Evidence Matrix.
- **MCP server as a separate Render service** — rejected 2026-05-26.
  Embedded in the backend works (stdio child) and avoids a second
  paid service. Re-evaluate if/when MCP HTTP becomes external-traffic-
  heavy.
- **Pure-LLM interpretation for MC / Sun / Houses** — rejected
  2026-06-28 (Phase 8). Hard archetype tables with cited classical
  sources (Sue Tompkins, Liz Greene, Howard Sasportas, Robert Hand,
  William Lilly) give confidence 0.9 instead of 0.7 and run at
  $0 cost — strictly better than LLM-on-the-fly for the well-known
  archetypal layer.
- **Chiron / asteroid transits via MOSEPH analytic ephemeris** —
  rejected 2026-06-14 (Phase 7). MOSEPH doesn't ship asteroids
  (`seas_18.se1` is required). Two options remain: drop Chiron from
  the transit list (current state) OR upload `.se1` files to a Cloud
  Storage bucket and point `SE_EPHE_PATH` at it (Phase 8 Cloud Run
  guide §8 documents the path).
