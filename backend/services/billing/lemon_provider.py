"""Lemon Squeezy (Merchant of Record) integration.

Lemon Squeezy handles VAT, sales tax, KYC, chargebacks. We just:
1. Create checkout sessions with a variant_id and user context.
2. Verify and consume webhook events to keep our Subscription rows
   in sync with Lemon's source of truth.

Docs: https://docs.lemonsqueezy.com/api

Env vars (see .env.example):
    LEMON_API_KEY              — server-side API key (Bearer)
    LEMON_STORE_ID             — numeric store id
    LEMON_WEBHOOK_SECRET       — HMAC-SHA256 secret for webhook verification
    LEMON_VARIANT_PREMIUM      — variant id for Premium subscription
    LEMON_VARIANT_PRO          — variant id for Pro (BYOK) subscription
    LEMON_VARIANT_NATAL_PDF    — variant id for the one-time detailed natal PDF
    LEMON_VARIANT_YEARLY       — variant id for the one-time yearly forecast
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

LEMON_API_BASE = "https://api.lemonsqueezy.com/v1"


# Map our internal product slug → env var holding the Lemon variant id.
PRODUCT_VARIANT_ENV = {
    "premium_monthly": "LEMON_VARIANT_PREMIUM",
    "pro_monthly": "LEMON_VARIANT_PRO",
    "natal_pdf": "LEMON_VARIANT_NATAL_PDF",
    "yearly_forecast": "LEMON_VARIANT_YEARLY",
}

# Map of variant id → (tier, is_subscription). Built lazily at runtime.
def _variant_to_tier() -> dict[str, tuple[str, bool]]:
    return {
        os.getenv("LEMON_VARIANT_PREMIUM", ""): ("premium", True),
        os.getenv("LEMON_VARIANT_PRO", ""): ("pro", True),
        os.getenv("LEMON_VARIANT_NATAL_PDF", ""): ("free", False),
        os.getenv("LEMON_VARIANT_YEARLY", ""): ("free", False),
    }


@dataclass
class CheckoutResult:
    url: str
    checkout_id: str


class LemonSqueezyError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.getenv("LEMON_API_KEY", "")
    if not key:
        raise LemonSqueezyError(
            "LEMON_API_KEY is not set — Lemon Squeezy provider unavailable."
        )
    return key


def _store_id() -> str:
    sid = os.getenv("LEMON_STORE_ID", "")
    if not sid:
        raise LemonSqueezyError("LEMON_STORE_ID is not set.")
    return sid


def variant_id_for(product_slug: str) -> str:
    env_var = PRODUCT_VARIANT_ENV.get(product_slug)
    if env_var is None:
        raise LemonSqueezyError(f"Unknown product slug: {product_slug}")
    variant = os.getenv(env_var, "")
    if not variant:
        raise LemonSqueezyError(
            f"{env_var} is not set — product '{product_slug}' not configured."
        )
    return variant


async def create_checkout(
    *,
    product_slug: str,
    user_id: str,
    user_email: str,
    locale: str = "en",
    success_redirect: Optional[str] = None,
) -> CheckoutResult:
    """Create a Lemon checkout URL for the given product slug.

    The user_id is embedded in `custom_data` so the webhook can attribute
    the subscription to the right user when it fires.
    """
    variant = variant_id_for(product_slug)
    store = _store_id()

    payload: dict[str, Any] = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user_email,
                    "custom": {"user_id": user_id, "product_slug": product_slug},
                },
                "checkout_options": {
                    "embed": False,
                    "media": True,
                    "logo": True,
                    "desc": True,
                    "discount": True,
                    "dark": False,
                    "subscription_preview": True,
                    "button_color": "#7c3aed",
                },
                "product_options": {
                    "redirect_url": success_redirect or "",
                    "receipt_button_text": "Return to OneiroScope",
                    "receipt_thank_you_note": "Thank you for supporting science-grounded astrology.",
                },
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": str(store)}},
                "variant": {"data": {"type": "variants", "id": str(variant)}},
            },
        }
    }

    headers = {
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
        "Authorization": f"Bearer {_api_key()}",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{LEMON_API_BASE}/checkouts", headers=headers, json=payload
        )
        if resp.status_code >= 400:
            logger.error(
                "Lemon checkout failed: %s %s", resp.status_code, resp.text[:500]
            )
            raise LemonSqueezyError(
                f"Lemon API {resp.status_code}: {resp.text[:200]}"
            )
        data = resp.json()["data"]
        return CheckoutResult(
            url=data["attributes"]["url"],
            checkout_id=str(data["id"]),
        )


def verify_webhook_signature(body: bytes, signature_header: str) -> bool:
    """HMAC-SHA256 verification per Lemon's docs.

    Compare in constant time; secret is `LEMON_WEBHOOK_SECRET`. Returns
    False on any mismatch (including missing secret in env).
    """
    secret = os.getenv("LEMON_WEBHOOK_SECRET", "")
    if not secret or not signature_header:
        return False
    expected = hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header.strip())


@dataclass
class WebhookEvent:
    """Normalized subset of a Lemon webhook payload."""

    event_name: str
    event_id: str
    user_id: Optional[str]
    product_slug: Optional[str]
    subscription_id: Optional[str]
    variant_id: Optional[str]
    customer_id: Optional[str]
    status: Optional[str]
    renews_at: Optional[str]
    ends_at: Optional[str]


def parse_webhook(payload: dict) -> WebhookEvent:
    """Pull the fields we care about out of Lemon's verbose payload."""
    meta = payload.get("meta") or {}
    data = payload.get("data") or {}
    attrs = data.get("attributes") or {}
    custom = (meta.get("custom_data") or {})

    return WebhookEvent(
        event_name=meta.get("event_name", "") or "",
        event_id=str(meta.get("event_id", "") or data.get("id", "") or ""),
        user_id=custom.get("user_id"),
        product_slug=custom.get("product_slug"),
        subscription_id=str(data.get("id")) if data.get("id") else None,
        variant_id=str(attrs.get("variant_id")) if attrs.get("variant_id") else None,
        customer_id=str(attrs.get("customer_id"))
        if attrs.get("customer_id")
        else None,
        status=attrs.get("status"),
        renews_at=attrs.get("renews_at"),
        ends_at=attrs.get("ends_at"),
    )


def tier_for_variant(variant_id: Optional[str]) -> str:
    """Lookup the tier ('premium' / 'pro' / 'free') for a webhook variant."""
    if not variant_id:
        return "free"
    mapping = _variant_to_tier()
    return mapping.get(variant_id, ("free", True))[0]
