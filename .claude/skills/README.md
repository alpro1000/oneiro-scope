# OneiroScope Skills

User-invocable commands for Claude Code that consume the OneiroScope MCP
server (`backend/mcp/`). Each skill lives in `<slug>/SKILL.md` with YAML
frontmatter (`name`, `description`).

| Skill              | Purpose                                                                          |
|--------------------|----------------------------------------------------------------------------------|
| `/natal`           | Full natal-chart workflow: validate inputs → calculate → summarize w/ provenance |
| `/horoscope`       | Daily / weekly / monthly / yearly horoscope (optionally personalized)            |
| `/dream`           | Hall/Van de Castle + Jungian + REM/NREM + DreamBank dream analysis               |
| `/lunar`           | Lunar-day info (single date or range), Swiss Ephemeris-backed                    |
| `/deploy-cycle`    | Pre-deploy gate: pytest + MCP smoke + frontend tests + env sanity                |
| `/validate-prod`   | Production env health-check (env vars, ephemeris, /health, lunar smoke)          |
| `/cost-report`     | LLM cost summary per provider (Phase 4 — partially wired)                        |
| `/research-symbol` | Add a new dream symbol to the knowledge base, methodologically grounded          |

## Conventions

- Skills MUST call MCP tools (`mcp__oneiro__*`), never FastAPI HTTP or
  the service classes directly. This rule is enforced in
  `docs/steering/structure.md`.
- For LLM-heavy operations (natal, horoscope, dream), validate inputs
  first using pure tools (`validate_birth_data`, `search_city`) to save
  cost.
- Detect user language from their message; pass `locale="ru"` or
  `locale="en"` consistently through the whole tool chain.
- At end of a substantial session (≥ 3 tool calls or any code change),
  append an entry to `docs/soul.md §9`.
