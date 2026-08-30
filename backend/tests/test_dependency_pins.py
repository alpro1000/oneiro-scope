"""Guards on the two lists CI and production each read separately.

Both failures this file pins were invisible while they were happening, and
both cost the connector rather than a test:

1. **The mcp ceiling.** `backend/requirements.txt` said `mcp>=1.23` with no
   upper bound. mcp 2.0.0 (2026-07-28) renamed `mcp.server.fastmcp.FastMCP` to
   `mcp.server.mcpserver.MCPServer`, so `backend/mcp/server.py` stopped
   importing — and `build_mcp_http_app()` catches that, leaving `/mcp`
   unmounted while `/health` stays green. Meanwhile `mcp-smoke.yml` carried its
   OWN specifier (`mcp[cli]>=1.2`) and pip happened to resolve it to 1.29.0, so
   CI was green against a dependency graph production does not install.

2. **The unrun test files.** That workflow names every test file it runs.
   Sixteen files had accumulated in `backend/tests/` that no workflow named —
   including `test_chart_core_contract.py`, the file asserting the MCP chart
   payload matches the HTTP one. It was red, and had been.

So: the pin is asserted against what is actually importable, the workflow's
copy of it is asserted against requirements.txt, and the file list is asserted
against the directory.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = REPO_ROOT / "backend" / "requirements.txt"
SMOKE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "mcp-smoke.yml"
TESTS_DIR = REPO_ROOT / "backend" / "tests"

# Files no workflow can run: they need dependencies deliberately left out of
# the light install. A filename → reason mapping, not a bare list, so the
# exemption cannot quietly become the place unrun files go: writing the reason
# is the moment you notice there isn't one.
NOT_IN_SMOKE_WORKFLOW: dict[str, str] = {}


def _requirement_specifier(name: str) -> str:
    """The full requirement line for `name` in backend/requirements.txt."""
    pattern = re.compile(rf"^{re.escape(name)}(?:\[[^\]]+\])?\s*[<>=!~]", re.M)
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and pattern.match(stripped):
            return stripped
    raise AssertionError(f"{name} is not pinned in backend/requirements.txt")


def test_mcp_is_pinned_below_the_major_that_renamed_fastmcp():
    """An open upper bound here decides which major production runs."""
    spec = _requirement_specifier("mcp")
    assert "<2" in spec.replace(" ", ""), (
        f"backend/requirements.txt pins mcp as {spec!r}. mcp 2.x renamed "
        "mcp.server.fastmcp to mcp.server.mcpserver, which stops "
        "backend/mcp/server.py from importing at all — and the failure is "
        "silent (the REST API boots, /mcp is simply absent). Port the server "
        "to MCPServer before raising this ceiling."
    )


def test_the_installed_mcp_actually_provides_what_the_server_imports():
    """The pin is a claim about the installed tree — check the tree.

    A ceiling in a text file protects nobody if the environment already holds
    a version above it (a stale venv, a cached CI image, a Render build that
    ran before the pin landed). This is the assertion that catches that, and
    it is the same import `backend/mcp/server.py` performs.
    """
    pytest.importorskip("mcp", reason="mcp SDK not installed in this environment")

    from mcp.server.fastmcp import FastMCP  # noqa: F401

    import mcp as mcp_pkg

    version = getattr(mcp_pkg, "__version__", None)
    if version is not None:
        assert not version.startswith("2."), (
            f"mcp {version} is installed; backend/mcp/server.py needs 1.x "
            "(FastMCP). Reinstall from backend/requirements.txt."
        )


def test_the_workflow_pins_mcp_exactly_as_requirements_does():
    """Two pin lists for one package is how CI came to test another graph."""
    required = _requirement_specifier("mcp").replace(" ", "")
    workflow = SMOKE_WORKFLOW.read_text(encoding="utf-8")

    in_workflow = re.findall(r'"(mcp(?:\[[^\]]+\])?[<>=!~][^"]*)"', workflow)
    assert in_workflow, "mcp-smoke.yml no longer installs mcp — check the job"
    for spec in in_workflow:
        assert spec.replace(" ", "") == required, (
            f"mcp-smoke.yml installs {spec!r} while backend/requirements.txt "
            f"says {required!r}. CI would be testing a dependency graph "
            "production never installs — which is exactly how mcp 2.x reached "
            "Render green."
        )


def test_every_backend_test_file_is_run_by_some_workflow():
    """A test file no workflow names is a test that does not exist."""
    workflows = REPO_ROOT / ".github" / "workflows"
    named: set[str] = set()
    for path in workflows.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        named.update(re.findall(r"backend/tests/(test_[a-z0-9_]+\.py)", text))
        # A whole-directory run covers everything at once.
        if re.search(r"pytest[^\n|]*\bbackend/tests/?(\s|$)", text):
            return

    on_disk = {p.name for p in TESTS_DIR.glob("test_*.py")}
    orphans = sorted(on_disk - named - set(NOT_IN_SMOKE_WORKFLOW))
    assert not orphans, (
        "these test files are run by no workflow, so they can be red for "
        f"months without anyone learning: {orphans}. Add them to "
        ".github/workflows/mcp-smoke.yml, or list them in "
        "NOT_IN_SMOKE_WORKFLOW here with the dependency that blocks them."
    )
