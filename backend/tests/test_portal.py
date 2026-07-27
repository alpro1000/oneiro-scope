"""Tests for the portal pages (landing, connect, pricing, legal).

Renders through the real router so a broken template or a stale key in the
content dict fails here rather than in production.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
pytest.importorskip("jinja2", reason="jinja2 not installed")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.portal.router import router  # noqa: E402
from backend.services.strategic.analysis_plan import STAGES  # noqa: E402


@pytest.fixture(scope="module")
def client():
    """Portal router alone — no DB, no MCP, no rate limiter."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/", "/connect", "/pricing", "/privacy", "/terms"])
def test_pages_render(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    # Jinja leaves unresolved expressions verbatim only on typos in raw text;
    # a missing key raises, so this guards against stray markup.
    assert "{{" not in resp.text


def test_landing_lists_every_analysis_stage(client):
    """The site's capability table is generated from the orchestrator."""
    body = client.get("/", headers={"accept-language": "ru"}).text
    for stage in STAGES:
        assert stage.name_ru in body, f"stage missing from landing: {stage.id}"


def test_connect_page_shows_the_configured_mcp_url(client, monkeypatch):
    monkeypatch.setattr(
        settings, "MCP_PUBLIC_URL", "https://api.example.com/mcp", raising=False
    )
    body = client.get("/connect").text
    assert "https://api.example.com/mcp" in body


def test_connect_page_falls_back_to_request_url(client, monkeypatch):
    monkeypatch.setattr(settings, "MCP_PUBLIC_URL", None, raising=False)
    monkeypatch.setattr(settings, "MCP_PATH", "/mcp", raising=False)
    body = client.get("/connect").text
    assert "/mcp" in body


def test_language_selection(client):
    ru = client.get("/", headers={"accept-language": "ru-RU,ru;q=0.9"}).text
    en = client.get("/", headers={"accept-language": "en-US,en;q=0.9"}).text
    assert "Астрология, сны и лица" in ru
    assert "Astrology, dreams and faces" in en
    # Explicit override wins over the header.
    forced = client.get("/?lang=en", headers={"accept-language": "ru"}).text
    assert "Astrology, dreams and faces" in forced


def test_every_page_carries_the_disclaimer(client):
    for path in ["/", "/connect", "/pricing", "/privacy", "/terms"]:
        body = client.get(path, headers={"accept-language": "ru"}).text
        assert "рефлексивно-развлекательный" in body, path


def test_legal_pages_state_the_hard_rules(client):
    """Directory review reads these; the claims must match what the code does."""
    privacy = client.get("/privacy", headers={"accept-language": "en"}).text
    assert "not persisted" in privacy
    assert "own photographs only" in privacy

    terms = client.get("/terms", headers={"accept-language": "en"}).text
    assert "no predictions" in terms.lower()
    assert "no scientific validity" in terms
