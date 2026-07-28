"""WP-6: every MCP tool response carries the versioning `meta` block.

Two layers of enforcement:
- structural: every `mcp.tool()(…)` registration in server.py goes
  through `with_meta` — no tool can be registered around the wrapper;
- runtime: representative sync/async tools actually return the block
  with all required fields, tz-aware timestamp and a reproducible
  input_hash.
"""

import ast
import asyncio
import re
from pathlib import Path

import pytest

from backend.mcp.tools._meta import COMMIT, SCHEMA_VERSION, SERVER_VERSION, with_meta

REPO = Path(__file__).resolve().parents[2]

REQUIRED_META_FIELDS = {
    "server_version", "commit", "schema_version", "request_id",
    "input_hash", "duration_ms", "cache_hit", "computed_at",
}


def test_every_registration_is_wrapped_with_meta():
    src = (REPO / "backend" / "mcp" / "server.py").read_text()
    tree = ast.parse(src)
    registrations = 0
    unwrapped = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Call):
            # mcp.tool()(X) — X must be with_meta(<module.attr>)
            registrations += 1
            arg = node.args[0]
            ok = (
                isinstance(arg, ast.Call)
                and getattr(arg.func, "id", None) == "with_meta"
            )
            if not ok:
                unwrapped.append(ast.unparse(arg))
    assert registrations > 0, "no registrations parsed — check would be vacuous"
    assert not unwrapped, f"tools registered without with_meta: {unwrapped}"


def test_meta_block_on_sync_tool():
    from backend.mcp.tools.dreams import list_hvdc_categories

    out = with_meta(list_hvdc_categories)(locale="ru")
    meta = out["meta"]
    assert REQUIRED_META_FIELDS <= set(meta)
    assert meta["server_version"] == SERVER_VERSION
    assert meta["schema_version"] == SCHEMA_VERSION
    assert meta["commit"] == COMMIT and meta["commit"] != ""
    assert meta["request_id"].startswith("req_")
    assert meta["input_hash"].startswith("sha256:")
    assert meta["cache_hit"] is False
    # tz-aware timestamp: explicit offset or Z, never a bare local string
    assert re.search(r"(Z|[+-]\d{2}:\d{2})$", meta["computed_at"])


@pytest.mark.asyncio
async def test_meta_block_on_async_tool_and_hash_stability():
    from backend.mcp.tools.dreams import analyze_dream

    wrapped = with_meta(analyze_dream)
    out1 = await wrapped(dream_text="Мне снилось спокойное поле без событий.", locale="ru")
    out2 = await wrapped(dream_text="Мне снилось спокойное поле без событий.", locale="ru")
    assert out1["meta"]["input_hash"] == out2["meta"]["input_hash"], (
        "identical input must produce identical input_hash"
    )
    assert out1["meta"]["request_id"] != out2["meta"]["request_id"]
    out3 = await wrapped(dream_text="Мне снилось совсем другое поле и река.", locale="ru")
    assert out3["meta"]["input_hash"] != out1["meta"]["input_hash"]


def test_dreams_response_timestamps_are_tz_aware():
    from datetime import datetime

    from backend.services.dreams.schemas import DreamAnalysisRequest
    from backend.services.dreams.service import DreamService

    resp = asyncio.run(
        DreamService().analyze_dream(
            DreamAnalysisRequest(dream_text="Тихий сон про поле и небо.", locale="ru"),
            interpret=False,
        )
    )
    assert isinstance(resp.analyzed_at, datetime)
    assert resp.analyzed_at.tzinfo is not None, "analyzed_at must be tz-aware"
    assert "+" in resp.analyzed_at.isoformat() or resp.analyzed_at.isoformat().endswith("Z")
