"""Tests for rate limiting middleware (Phase 2)."""

import pytest
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.middleware.rate_limit import RateLimitMiddleware, RateLimitInfo


def test_rate_limit_info_creation():
    """Test RateLimitInfo initialization."""
    limiter = RateLimitInfo(limit=10, window_seconds=60)

    assert limiter.limit == 10
    assert limiter.window_seconds == 60
    assert limiter.remaining() == 10


def test_rate_limit_info_allows_requests():
    """Test that RateLimitInfo allows requests within limit."""
    limiter = RateLimitInfo(limit=3, window_seconds=60)

    # First 3 requests should be allowed
    assert limiter.is_allowed() is True
    assert limiter.is_allowed() is True
    assert limiter.is_allowed() is True

    # 4th request should be denied
    assert limiter.is_allowed() is False
    assert limiter.remaining() == 0


def test_rate_limit_info_tracks_remaining():
    """Test that remaining() returns correct count."""
    limiter = RateLimitInfo(limit=5, window_seconds=60)

    assert limiter.remaining() == 5
    limiter.is_allowed()
    assert limiter.remaining() == 4
    limiter.is_allowed()
    assert limiter.remaining() == 3


def test_rate_limit_info_window_expiry():
    """Test that requests outside window are removed."""
    limiter = RateLimitInfo(limit=2, window_seconds=1)

    # Fill the limit
    assert limiter.is_allowed() is True
    assert limiter.is_allowed() is True
    assert limiter.is_allowed() is False

    # Wait for window to pass (in real code this would be time.sleep)
    # For this test, we'll manually manipulate timestamps
    limiter.requests = [
        datetime.utcnow() - timedelta(seconds=2),
        datetime.utcnow() - timedelta(seconds=2)
    ]

    # Now requests outside window should be cleaned and new requests allowed
    assert limiter.is_allowed() is True


def test_rate_limit_middleware_integration():
    """Test RateLimitMiddleware with FastAPI app."""
    app = FastAPI()

    # Add middleware with low limit for testing
    app.add_middleware(RateLimitMiddleware, per_user_limit=2)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # First request should succeed
    response1 = client.get("/test")
    assert response1.status_code == 200
    assert "X-RateLimit-Limit" in response1.headers
    assert response1.headers["X-RateLimit-Limit"] == "2"
    assert response1.headers["X-RateLimit-Remaining"] == "1"

    # Second request should succeed
    response2 = client.get("/test")
    assert response2.status_code == 200
    assert response2.headers["X-RateLimit-Remaining"] == "0"

    # Third request should be rate limited
    response3 = client.get("/test")
    assert response3.status_code == 429
    assert "Rate limit exceeded" in response3.json()["detail"]
    assert response3.json()["remaining"] == 0
    assert "reset_at" in response3.json()


def test_rate_limit_middleware_different_ips():
    """Test that rate limiting is per-IP."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, per_user_limit=1)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    # TestClient uses same IP by default, so we test with different clients
    # but the same client instance will be rate limited
    client1 = TestClient(app)

    # Client 1 makes request
    response1a = client1.get("/test")
    assert response1a.status_code == 200

    # Client 1 second request should be rate limited (same IP)
    response1b = client1.get("/test")
    assert response1b.status_code == 429

    # For testing different IPs, we'd need to mock the request.client.host
    # This is a limitation of TestClient - in production, different clients have different IPs
    # So this test verifies that a single client is properly rate limited


def test_rate_limit_is_per_forwarded_client_not_per_proxy():
    """Behind Render the socket peer is the proxy, so keying on it would put
    every user in one bucket. Distinct X-Forwarded-For clients must not
    rate-limit each other."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, per_user_limit=1)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # User A spends their single request.
    a1 = client.get("/test", headers={"x-forwarded-for": "203.0.113.7"})
    assert a1.status_code == 200
    a2 = client.get("/test", headers={"x-forwarded-for": "203.0.113.7"})
    assert a2.status_code == 429

    # User B, same proxy, different real IP — must still be allowed.
    b1 = client.get("/test", headers={"x-forwarded-for": "203.0.113.8"})
    assert b1.status_code == 200


def test_forwarded_client_is_taken_spoof_resistant():
    """The rightmost XFF entry (what the trusted proxy observed) is used, so a
    client prepending a fake IP cannot mint a fresh bucket each request."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, per_user_limit=1)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # Attacker varies the LEFT (client-controlled) part; the proxy-appended
    # real IP on the right stays constant, so the second call is still limited.
    first = client.get("/test", headers={"x-forwarded-for": "1.1.1.1, 203.0.113.9"})
    assert first.status_code == 200
    second = client.get("/test", headers={"x-forwarded-for": "2.2.2.2, 203.0.113.9"})
    assert second.status_code == 429


def test_rate_limit_headers_include_reset_time():
    """Test that rate limit headers include reset time."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, per_user_limit=1)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # Make one request
    response = client.get("/test")
    assert response.status_code == 200

    # Check headers
    assert "X-RateLimit-Reset" in response.headers
    reset_time_str = response.headers["X-RateLimit-Reset"]
    # Should be a valid ISO format datetime
    assert "T" in reset_time_str


@pytest.mark.asyncio
async def test_rate_limit_middleware_headers_on_allowed():
    """Test that rate limit headers are present on allowed requests."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, per_user_limit=10)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200
    assert response.headers.get("X-RateLimit-Limit") == "10"
    assert int(response.headers.get("X-RateLimit-Remaining")) < 10
