# {FEATURE} — Tasks

> **English TL;DR:** Ordered checklist derived from design.md. Each
> checkbox = one commit. Each major Gate = one merged commit on the
> feature branch. Test plan is co-located.

**Feature:** {slug}
**Branch:** `claude/{slug}-{rand5}`
**Status:** in-progress | done | abandoned
**Updated:** YYYY-MM-DD

---

## Pre-flight

- [ ] Read `docs/steering/{conventions,domain,structure,tech}.md` —
      confirm no new ADR needed (or add to `soul.md §6`).
- [ ] Run baseline tests on `main` — record current pass count.
- [ ] Confirm branch name follows `claude/<task>-<5chars>` pattern.

## Gate 1 — Pure substrate

- [ ] New service module in `backend/services/{domain}/{name}.py`
      with pure-function API (no side effects).
- [ ] Unit tests for the substrate (`backend/tests/test_{name}.py`).
- [ ] Commit: `feat({scope}): add {substrate} substrate`

## Gate 2 — MCP tool wrapper

- [ ] MCP tool wrapper in `backend/mcp/tools/{name}.py`.
- [ ] Returns `{layer, confidence, ..., source, disclaimer}`.
- [ ] Registered in `backend/mcp/server.py`.
- [ ] Smoke test added to `backend/tests/test_mcp_smoke.py` registry.
- [ ] Commit: `feat(mcp): expose {tool} as MCP tool`

## Gate 3 — Agent integration

- [ ] Tool added to `StrategicAnalystAgent.allowed_tools` (and any
      specialist that should use it).
- [ ] Updated `agents/prompts/{specialist}_system.md` if the tool
      changes how the agent should respond.
- [ ] Updated `backend/tests/test_strategic_agent.py` allowed-tools
      assertion.
- [ ] Commit: `feat(agents): wire {tool} into {agent}`

## Gate 4 — Documentation

- [ ] Update `docs/steering/{tech,structure,domain}.md` if architecture
      moved.
- [ ] Update `docs/PLAN.md` if this feature corresponds to a phase item.
- [ ] Update `docs/next-session.md` with the new "what works" line.
- [ ] Commit: `docs: document {feature}`

## Gate 5 — CI + smoke

- [ ] All new tests added to `.github/workflows/mcp-smoke.yml`.
- [ ] Full backend suite green locally.
- [ ] Push branch + create PR.

## Gate 6 — Merge

- [ ] CI smoke green.
- [ ] Address any Amazon Q / human review comments.
- [ ] Squash-merge to `main`.
- [ ] Append session log to `docs/soul.md §9` — what landed, decisions,
      deferred.

---

## Test plan

| Test | What it locks in | File |
|---|---|---|
| `test_{name}_signature` | Required fields present | `test_{name}.py` |
| `test_{name}_layer_is_correct` | layer/confidence per scaffold | same |
| `test_{name}_carries_disclaimer` | disclaimer enforcement | same |
| `test_{name}_no_determinism` | language guard | same |
| `test_mcp_smoke::test_all_tools_registered` | MCP registry includes new tool | `test_mcp_smoke.py` |
| `test_strategic_agent::test_strategic_agent_has_all_decision_support_tools` | Agent allowed_tools updated | `test_strategic_agent.py` |

## Deferred (track here, address in follow-up PR)

- [ ] {thing we explicitly deferred — link to next-session.md if owner-visible}
