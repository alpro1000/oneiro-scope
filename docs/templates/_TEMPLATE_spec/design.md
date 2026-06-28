# {FEATURE} — Design

> **English TL;DR:** How we'll build it. Layering, data flow, key
> types, integration points. Reviewed against requirements.md BEFORE
> writing tasks.md.

**Feature:** {slug}
**Owner:** ...
**Status:** draft | accepted | implemented
**Updated:** YYYY-MM-DD

---

## §1 Architecture sketch

ASCII diagram showing where this feature sits in the OneiroScope
layer stack:

```
Skills (.claude/skills/) → Agents (agents/) → MCP tools (backend/mcp/)
   → Services (backend/services/) → DB / external APIs
```

(Where does this feature live? Which layers does it touch?)

## §2 Data flow

User → ... → ... → User.

Step-by-step what happens.

## §3 New / changed components

| Component | New / Changed | Confidence layer | Notes |
|---|---|---|---|
| `backend/services/X/y.py` | New | — | Pure computation |
| `backend/mcp/tools/X.py` | New | astrology_symbolic / 0.9 | Wraps the service |
| `agents/prompts/X_system.md` | Changed | — | Updated tool list |

## §4 Public contracts

### MCP tool signatures

```python
async def tool_name(arg1: str, arg2: int = 5) -> dict[str, Any]:
    """Returns {layer, confidence, ..., source, disclaimer}."""
```

### Pydantic schemas

```python
class FeatureRequest(BaseModel):
    ...
class FeatureResponse(BaseModel):
    ...
```

## §5 Confidence ladder mapping

Per `docs/steering/domain.md`:
- Astronomy parts → 1.0
- Hard-table archetypes → 0.9
- Symbol dictionary → 0.8
- LLM synthesis → 0.7

What's this feature's contribution at each tier?

## §6 Disclaimer & ethics check

- Does this feature surface interpretive content? → Wrap with
  `ensure_disclaimer()`.
- Does it touch forbidden topics from `domain.md §5`? → Refuse path
  defined here.
- Does it use deterministic-prediction language? → Validated by
  `contains_determinism()`.

## §7 Integration with existing components

- Affects `agents/orchestrator.py`? (intent routing)
- Affects `agents/specialists/strategic_agent.py`? (tool allowlist)
- Affects `backend/mcp/server.py`? (tool registration)
- Affects `agents/prompts/*.md`? (which prompts mention new tool)

## §8 Test strategy

- **Unit:** what to mock, what to test directly.
- **Integration:** which MCP tools to exercise end-to-end.
- **Provenance check:** every response has `source` + `disclaimer`.
- **No exact-text assertions** for interpretive content.

## §9 Migration / rollback

- Data migration needed? (Alembic step)
- Feature flag? (Lemon Squeezy variant gating?)
- Rollback plan if it breaks in prod.

## §10 Trade-offs we accepted

- Cost vs latency: ...
- Determinism vs flexibility: ...
- Premium-only vs free: ...
