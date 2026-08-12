"""`/health` must say which build is answering.

The story this file exists for: production served a build twelve days old
while the owner tested it and wrote up three defects in careful detail. All
three were real, and all three had been fixed nine days earlier in a single
commit. Nothing was wrong with the code and nothing was wrong with the report
— the only broken thing was that a stale deploy is invisible. `/health`
answered "healthy" the whole time, truthfully.

So the build identity is now part of the health contract, and
`.github/workflows/keepalive.yml` compares it against the default branch on
every ping. These tests protect the two halves of that: the field is present,
and the shell in the workflow can actually extract it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def test_health_response_declares_the_commit():
    from backend.api.v1.health import HealthResponse

    assert "commit" in HealthResponse.model_fields, (
        "the deployed commit left the /health contract — keepalive.yml can no "
        "longer tell a stale deploy from a current one"
    )


@pytest.mark.asyncio
async def test_health_reports_a_real_commit():
    from backend.api.v1.health import health_check

    body = await health_check()
    assert body["commit"], "empty commit tells the operator nothing"
    # Either a real sha (Render sets RENDER_GIT_COMMIT) or the honest
    # "unknown" for a checkout that has none — never a plausible-looking
    # placeholder, which is worse than an admission.
    assert body["commit"] == "unknown" or re.fullmatch(r"[0-9a-f]{7,40}", body["commit"]), (
        body["commit"]
    )


def test_the_workflow_can_extract_the_commit_it_greps_for():
    """The workflow parses JSON with `sed`. That is fine for one flat field
    and fragile the moment the field moves, so the exact expression the
    workflow runs is executed here against a realistic payload — a check that
    lives only in a YAML file is a check nobody runs until it is needed."""
    workflow = (REPO / ".github" / "workflows" / "keepalive.yml").read_text()
    match = re.search(r"sed -n '(s/[^']*commit[^']*)'", workflow)
    assert match, "the commit-extracting sed expression is gone from keepalive.yml"

    payload = (
        '{"status": "healthy", "service": "OneiroScope", "version": "1.5.0", '
        '"commit": "276dce94b653", "ephemeris": {"engine": "SWIEPH"}}'
    )
    out = subprocess.run(
        ["sed", "-n", match.group(1)],
        input=payload, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert out == "276dce94b653", f"workflow would read {out!r} as the commit"


def test_the_staleness_check_fails_rather_than_warns_when_a_deploy_is_missing():
    """A warning in a scheduled workflow is read by nobody: the run stays
    green and green runs are not opened. Twelve days of staleness has to
    produce a failing run, which is the only thing that sends mail."""
    workflow = (REPO / ".github" / "workflows" / "keepalive.yml").read_text()
    assert "::error::" in workflow.split("Deployed commit")[1], (
        "the staleness check no longer fails — it can only warn, and a warning "
        "on a green scheduled run is indistinguishable from silence"
    )
