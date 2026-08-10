"""CORS: the misconfiguration that looks like a healthy server.

This is worth its own file because of how the failure presents. When
`ALLOWED_ORIGINS` is wrong, nothing on the server side goes wrong: the request
is routed, handled and answered 200, `/health` is green and the log is clean.
The response simply arrives without an `Access-Control-Allow-Origin` header, so
the browser discards it and the user sees "Failed to fetch". Every signal the
operator can see says the service is fine.

That is exactly what happened in production — the variable was `sync: false` in
`render.yaml`, was never set in the dashboard, and the development default
(`http://localhost:3000`) silently applied to a deployed site. These tests pin
the two halves of the fix: the header really is emitted for a configured
origin, and the bad configuration announces itself instead of hiding.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import Settings

FRONTEND = "https://oneiroscope.vercel.app"


def _app(settings: Settings) -> FastAPI:
    """A minimal app wired exactly the way `backend.app.main` wires CORS."""
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/lunar")
    async def lunar():
        return {"ok": True}

    @app.post("/api/v1/auth/login")
    async def login():
        return {"ok": True}

    return app


async def _request(app: FastAPI, method: str, path: str, headers: dict):
    """Drive the app over ASGI rather than through `TestClient`.

    Same middleware, same request, but no dependency on the httpx/starlette
    pairing that `TestClient` is sensitive to — this file is about a header,
    and it should not go red because a test-client constructor changed.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://api.example"
    ) as client:
        return await client.request(method, path, headers=headers)


# --- the header itself --------------------------------------------------------


@pytest.mark.anyio
async def test_a_configured_origin_gets_the_header_back():
    app = _app(Settings(ALLOWED_ORIGINS=FRONTEND, ENVIRONMENT="production"))
    resp = await _request(app, "GET", "/api/v1/lunar", {"Origin": FRONTEND})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == FRONTEND


@pytest.mark.anyio
async def test_the_broken_configuration_reproduces_the_reported_symptom():
    """The exact production state: defaults left in place, deployed frontend.

    Note what this asserts — a 200 with no CORS header. The request succeeded.
    Nothing here is an error the server could log. That is the whole reason the
    startup warning and the diagnostics row exist.
    """
    app = _app(Settings(ENVIRONMENT="production"))  # default localhost only
    resp = await _request(app, "GET", "/api/v1/lunar", {"Origin": FRONTEND})
    assert resp.status_code == 200
    assert "access-control-allow-origin" not in resp.headers


@pytest.mark.anyio
async def test_the_preflight_for_a_json_post_passes():
    """`/auth/login` failed at preflight, not at the request — cover both."""
    app = _app(Settings(ALLOWED_ORIGINS=FRONTEND, ENVIRONMENT="production"))
    resp = await _request(app, "OPTIONS", "/api/v1/auth/login", {
        "Origin": FRONTEND,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == FRONTEND
    assert resp.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.anyio
async def test_several_origins_and_a_custom_domain_can_coexist():
    app = _app(Settings(
        ALLOWED_ORIGINS=f"{FRONTEND}, https://oneiroscope.com",
        ENVIRONMENT="production",
    ))
    for origin in (FRONTEND, "https://oneiroscope.com"):
        resp = await _request(app, "GET", "/api/v1/lunar", {"Origin": origin})
        assert resp.headers.get("access-control-allow-origin") == origin


@pytest.mark.anyio
async def test_an_unlisted_origin_is_still_refused():
    """The fix must not turn into `allow_origins=["*"]` by accident.

    With `allow_credentials=True` a wildcard would hand session cookies to any
    site that asks, so the allow-list has to keep saying no.
    """
    app = _app(Settings(ALLOWED_ORIGINS=FRONTEND, ENVIRONMENT="production"))
    resp = await _request(
        app, "GET", "/api/v1/lunar", {"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in resp.headers


@pytest.mark.anyio
async def test_the_preview_regex_is_opt_in_and_bounded():
    """Vercel preview deploys, without opening the door to `*.vercel.app`."""
    app = _app(Settings(
        ALLOWED_ORIGINS=FRONTEND,
        ALLOWED_ORIGIN_REGEX=r"^https://oneiroscope-[a-z0-9-]+-alpro1000\.vercel\.app$",
        ENVIRONMENT="production",
    ))

    preview = "https://oneiroscope-abc123-alpro1000.vercel.app"
    resp = await _request(app, "GET", "/api/v1/lunar", {"Origin": preview})
    assert resp.headers.get("access-control-allow-origin") == preview

    # Someone else's project on the same shared domain must not match.
    other = await _request(
        app, "GET", "/api/v1/lunar", {"Origin": "https://someone-else-xyz.vercel.app"})
    assert "access-control-allow-origin" not in other.headers


# --- and the part that makes it visible ---------------------------------------


def test_production_on_the_development_default_is_reported():
    problem = Settings(ENVIRONMENT="production").cors_problem()
    assert problem is not None
    # The message has to name the variable — whoever reads it is looking at a
    # dashboard, not at this file.
    assert "ALLOWED_ORIGINS" in problem


def test_a_correct_production_setup_reports_nothing():
    assert Settings(
        ALLOWED_ORIGINS=FRONTEND, ENVIRONMENT="production"
    ).cors_problem() is None


def test_the_regex_alone_counts_as_configured():
    assert Settings(
        ALLOWED_ORIGINS="",
        ALLOWED_ORIGIN_REGEX=r"^https://x\.example$",
        ENVIRONMENT="production",
    ).cors_problem() is None


def test_localhost_in_development_is_not_a_problem():
    assert Settings(ENVIRONMENT="development").cors_problem() is None


def test_an_empty_allow_list_is_a_problem_even_in_development():
    """Nothing configured anywhere means no browser can call the API at all."""
    assert Settings(ALLOWED_ORIGINS="", ENVIRONMENT="development").cors_problem()


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("oneiroscope.vercel.app", ["https://oneiroscope.vercel.app"]),
        (f" {FRONTEND} , ", [FRONTEND]),
        (f"{FRONTEND},http://localhost:3000", [FRONTEND, "http://localhost:3000"]),
    ],
)
def test_origins_are_normalised_the_way_the_docs_promise(raw, expected):
    assert Settings(ALLOWED_ORIGINS=raw).allowed_origins_list == expected


def test_the_blueprint_ships_a_real_origin_rather_than_a_dashboard_promise():
    """`sync: false` is how this broke: the variable existed only as a prompt.

    Pinning it in the blueprint is what makes the deployed configuration
    reproducible from the repository — and what makes this fix arrive with the
    deploy instead of waiting on someone opening a dashboard.
    """
    from pathlib import Path

    blueprint = Path(__file__).resolve().parents[2] / "render.yaml"
    text = blueprint.read_text(encoding="utf-8")
    assert "value: https://oneiroscope.vercel.app" in text, (
        "ALLOWED_ORIGINS lost its concrete value in render.yaml"
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"
