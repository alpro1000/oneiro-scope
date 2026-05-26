# Steering — Technology

Architectural decisions log. Update on every significant tech choice.

## Backend

- **Language/runtime:** Python 3.11+.
- **Framework:** FastAPI (async). Pydantic v2 for all I/O contracts.
- **Astronomical core:** Swiss Ephemeris (`pyswisseph`). Prefers SWIEPH (binary files) over MOSEPH analytic. Path via `SE_EPHE_PATH` env.
- **Database:** PostgreSQL 15 (Render managed). SQLite for local dev. Alembic for migrations (not yet wired — `§5` in soul).
- **Cache:** Redis 7 (optional but recommended).
- **LLM providers (cost-ordered, first available wins):**
  1. Groq — `llama-3.1-8b-instant` (free tier).
  2. Gemini — `gemini-1.5-flash` ($0.075/1M).
  3. Together AI — Meta-Llama-3.1-8B ($0.20/1M).
  4. OpenAI — `gpt-4o-mini` ($0.15/1M).
  5. Anthropic — `claude-3-haiku-20240307` ($0.25/1M).
  Provider abstraction in `backend/core/llm_provider.py`. Every LLM call has a deterministic template fallback (no mocks).

## Frontend

- **Framework:** Next.js 14 (App Router). TypeScript strict.
- **Styling:** Tailwind CSS + Framer Motion.
- **i18n:** `next-intl`, locales `ru` / `en`, default `ru`.
- **Data:** Server components for SSR fetches, client components only when interactive (forms, voice input).

## MCP / Agents (new — 2026-05-26)

- **MCP SDK:** Python `mcp` package (FastMCP server). Transports: stdio (Claude Desktop), HTTP (remote agents).
- **Agent SDK:** Claude Agent SDK (`claude-agent-sdk` Python). Default model: `claude-opus-4-7`.
- **Layering rule:** MCP is the canonical tool surface. The ADK agent and skills consume MCP tools — they MUST NOT call FastAPI services directly. FastAPI services are the implementation; MCP is the boundary; agent/skills are consumers.
- **Tool naming:** snake_case verbs (`calculate_natal_chart`, `analyze_dream`, `search_city`). Tool descriptions are Pydantic docstrings — keep them precise; LLMs read them to decide invocation.

## Infrastructure

- **Container:** Docker (multi-stage). `docker-compose.yml` for local stack (Postgres + Redis + Redis Commander).
- **Deploy:** Render.com blueprint (`render.yaml`). Backend Python web service, frontend Node web service, managed Postgres + Redis.
- **CI:** GitHub Actions — backend pytest, frontend jest, ETL pipeline check, repo inventory.

## Observability (planned)

- Structured logging via `backend/core/logging.py`.
- LLM cost tracker in Redis (planned — Phase 4).
- Ephemeris-mode log on startup (planned — Phase 4).

## Security

- No secrets in git. Render manages secrets (`sync: false` in blueprint).
- CORS: explicit origins via `ALLOWED_ORIGINS` env.
- Rate limiting middleware exists (`backend/middleware/rate_limit.py`) — per-user + global.
- MCP HTTP transport will require Bearer token (Phase 4).

## Versioning

- API: `/api/v1/*`. Breaking changes → `/api/v2/*`, not in-place edits.
- MCP tools: stable names; add new, deprecate old via metadata, don't rename.
