"""Response versioning for every MCP tool (WP-6).

The July-2026 audit spent half a day chasing a discrepancy between two
live runs that a single version field would have explained instantly:
57 saved responses carried no server_version, commit, schema_version or
request_id. Every tool response now carries a `meta` block:

    "meta": {
      "server_version": "1.5.0",
      "commit": "a3f91c2",
      "schema_version": "2",
      "request_id": "req_…",
      "input_hash": "sha256:…",   # canonical hash of the tool arguments
      "duration_ms": 1356,
      "cache_hit": false,          # no tool-level cache exists today
      "computed_at": "2026-07-28T15:23:01.679+00:00"
    }

`input_hash` is computed from the normalized (sorted-key JSON) bound
arguments, so two runs can prove they received identical input.
Timestamps always carry an explicit UTC offset — a bare ISO string
cannot prove it is UTC.

Wiring: `server.py` wraps every registration as
`mcp.tool()(with_meta(fn))` — one choke point, no per-tool code.
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "2"
SERVER_VERSION = "1.5.0"


def _resolve_commit() -> str:
    """Deployed commit: Render exposes RENDER_GIT_COMMIT; local checkouts
    fall back to git. 'untracked' is an explicit value, not a silent null —
    it means the process runs outside both Render and a git checkout."""
    for var in ("RENDER_GIT_COMMIT", "GIT_COMMIT"):
        value = os.getenv(var)
        if value:
            return value[:12]
    try:
        repo_root = Path(__file__).resolve().parents[3]
        out = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "untracked"


COMMIT = _resolve_commit()


def _input_hash(fn, args: tuple, kwargs: dict) -> str:
    try:
        bound = inspect.signature(fn).bind_partial(*args, **kwargs)
        bound.apply_defaults()
        payload = {k: v for k, v in bound.arguments.items()}
    except TypeError:
        payload = {"args": list(args), "kwargs": kwargs}
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _build_meta(fn, args: tuple, kwargs: dict, started: float) -> dict[str, Any]:
    return {
        "server_version": SERVER_VERSION,
        "commit": COMMIT,
        "schema_version": SCHEMA_VERSION,
        "request_id": "req_" + uuid.uuid4().hex[:16],
        "input_hash": _input_hash(fn, args, kwargs),
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "cache_hit": False,  # no tool-level cache exists; field kept for the contract
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }


def _attach(result: Any, meta: dict) -> Any:
    if isinstance(result, dict) and "meta" not in result:
        result["meta"] = meta
    return result


def with_meta(fn):
    """Wrap a tool so its dict response carries the `meta` block.

    Preserves name/doc/signature (FastMCP builds the tool schema from
    them). Works for sync and async tools alike."""
    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            started = time.perf_counter()
            result = await fn(*args, **kwargs)
            return _attach(result, _build_meta(fn, args, kwargs, started))

        return async_wrapper

    @functools.wraps(fn)
    def sync_wrapper(*args, **kwargs):
        started = time.perf_counter()
        result = fn(*args, **kwargs)
        return _attach(result, _build_meta(fn, args, kwargs, started))

    return sync_wrapper
