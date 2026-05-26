---
name: deploy-cycle
description: Run the OneiroScope production deploy cycle — backend pytest, frontend tests, MCP smoke, build verification, and Render deploy readiness check. Use when the user asks to "deploy", "ship", "release", or invokes /deploy-cycle. Does NOT push to Render automatically — surfaces a green/red status checklist.
---

# /deploy-cycle — Production deploy cycle

## What this does

A staged pre-deploy gate. Stops at the first failing stage and reports.
Does **not** trigger a Render deploy — Render auto-deploys on push to
main and the owner controls when to merge.

## Stages

1. **Backend tests** — `pytest backend/tests/ -q`
2. **MCP smoke** — `pytest backend/tests/test_mcp_smoke.py backend/tests/test_agent_smoke.py -v`
3. **Frontend tests** — `cd frontend && npm test --silent` (only if
   `frontend/package.json` exists and `npm test` script defined).
4. **Backend import smoke** — `python -c "import backend.app.main"`
5. **Render env sanity** — verify `render.yaml` has `ENVIRONMENT=production`
   on the backend service (NOT `development`) — surface a warning if not.
6. **Git status** — verify no uncommitted changes; if dirty, list them.
7. **Branch check** — verify we are on the branch named in the active
   task (CLAUDE.md mandatory block).

## Output format

A checklist:

```
✅ Backend tests        (38 passed, 6 skipped)
✅ MCP smoke           (14 passed)
⚠️  Frontend tests      (skipped — no frontend/package.json)
✅ Backend imports
🔴 Render env          (ENVIRONMENT=development — fix before deploy)
✅ Git status          (clean)
✅ Branch              (claude/eager-noether-5UQJR)
```

## Behavior

- Run stages in order; on first 🔴 failure, stop and surface the error.
- ⚠️ warnings (skips, non-blocking issues) accumulate but don't stop.
- After all stages green: report ready-to-deploy + remind the owner that
  Render deploys on merge to main, NOT on this branch.

## What this does NOT do

- Push to git.
- Trigger Render deploys.
- Modify any files.
