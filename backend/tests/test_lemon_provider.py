"""Lemon Squeezy provider tests (Phase 6.C).

Pure unit tests — no network. Webhook signature, payload parsing,
tier mapping, env-driven product config.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from backend.services.billing import lemon_provider


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("LEMON_API_KEY", "test-api-key")
    monkeypatch.setenv("LEMON_STORE_ID", "12345")
    monkeypatch.setenv("LEMON_WEBHOOK_SECRET", "shhh-secret")
    monkeypatch.setenv("LEMON_VARIANT_PREMIUM", "premium-9001")
    monkeypatch.setenv("LEMON_VARIANT_PRO", "pro-9002")
    monkeypatch.setenv("LEMON_VARIANT_NATAL_PDF", "pdf-9003")
    monkeypatch.setenv("LEMON_VARIANT_YEARLY", "yearly-9004")


def _signed(body: dict) -> tuple[bytes, str]:
    raw = json.dumps(body).encode("utf-8")
    sig = hmac.new(b"shhh-secret", raw, hashlib.sha256).hexdigest()
    return raw, sig


def test_verify_webhook_signature_accepts_valid():
    body, sig = _signed({"hello": "world"})
    assert lemon_provider.verify_webhook_signature(body, sig) is True


def test_verify_webhook_signature_rejects_tampered():
    body, sig = _signed({"hello": "world"})
    bad = sig[:-2] + "00"
    assert lemon_provider.verify_webhook_signature(body, bad) is False


def test_verify_webhook_signature_rejects_missing():
    body, _ = _signed({"a": 1})
    assert lemon_provider.verify_webhook_signature(body, "") is False


def test_verify_webhook_signature_unset_secret_returns_false(monkeypatch):
    monkeypatch.delenv("LEMON_WEBHOOK_SECRET", raising=False)
    body, sig = _signed({"a": 1})  # signature computed with old secret
    assert lemon_provider.verify_webhook_signature(body, sig) is False


def test_variant_id_for_known_slug():
    assert lemon_provider.variant_id_for("premium_monthly") == "premium-9001"
    assert lemon_provider.variant_id_for("pro_monthly") == "pro-9002"


def test_variant_id_for_unknown_slug_raises():
    with pytest.raises(lemon_provider.LemonSqueezyError):
        lemon_provider.variant_id_for("nonexistent")


def test_variant_id_for_unset_env_raises(monkeypatch):
    monkeypatch.delenv("LEMON_VARIANT_PREMIUM", raising=False)
    with pytest.raises(lemon_provider.LemonSqueezyError):
        lemon_provider.variant_id_for("premium_monthly")


def test_tier_for_variant():
    assert lemon_provider.tier_for_variant("premium-9001") == "premium"
    assert lemon_provider.tier_for_variant("pro-9002") == "pro"
    assert lemon_provider.tier_for_variant("pdf-9003") == "free"
    assert lemon_provider.tier_for_variant("unknown") == "free"
    assert lemon_provider.tier_for_variant(None) == "free"


def test_parse_webhook_subscription_created():
    payload = {
        "meta": {
            "event_name": "subscription_created",
            "event_id": "evt-001",
            "custom_data": {
                "user_id": "abc-123",
                "product_slug": "premium_monthly",
            },
        },
        "data": {
            "id": "lemon-sub-555",
            "attributes": {
                "variant_id": "premium-9001",
                "customer_id": "cust-77",
                "status": "active",
                "renews_at": "2026-07-01T00:00:00.000000Z",
                "ends_at": None,
            },
        },
    }
    event = lemon_provider.parse_webhook(payload)
    assert event.event_name == "subscription_created"
    assert event.event_id == "evt-001"
    assert event.user_id == "abc-123"
    assert event.product_slug == "premium_monthly"
    assert event.subscription_id == "lemon-sub-555"
    assert event.variant_id == "premium-9001"
    assert event.customer_id == "cust-77"
    assert event.status == "active"
    assert event.renews_at == "2026-07-01T00:00:00.000000Z"


def test_parse_webhook_handles_missing_custom_data():
    payload = {"meta": {"event_name": "subscription_updated"}, "data": {}}
    event = lemon_provider.parse_webhook(payload)
    assert event.user_id is None
    assert event.product_slug is None
    assert event.event_name == "subscription_updated"


def test_unset_api_key_raises_on_use(monkeypatch):
    monkeypatch.delenv("LEMON_API_KEY", raising=False)
    with pytest.raises(lemon_provider.LemonSqueezyError):
        lemon_provider._api_key()


def test_unset_store_id_raises_on_use(monkeypatch):
    monkeypatch.delenv("LEMON_STORE_ID", raising=False)
    with pytest.raises(lemon_provider.LemonSqueezyError):
        lemon_provider._store_id()
