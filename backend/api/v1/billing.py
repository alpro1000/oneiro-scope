"""Billing endpoints — Phase 6.C.

POST /billing/checkout — create a Lemon Squeezy checkout URL.
POST /billing/webhook  — Lemon's HMAC-signed webhook receiver.
GET  /billing/me       — current subscription summary.

Webhooks are idempotent: each Lemon `event_id` is recorded in an
in-memory set (would move to Redis/DB in production).
"""

from __future__ import annotations

import logging
from datetime import datetime
from threading import Lock
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.api.v1.auth import get_current_user_db
from backend.core.database import get_db
from backend.models.subscription import Subscription
from backend.models.user import User
from backend.services.billing import lemon_provider
from backend.services.billing.quotas import current_tier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

# Idempotency set — production should use Redis/DB.
_WEBHOOK_SEEN_LOCK = Lock()
_WEBHOOK_SEEN: set[str] = set()


def _seen(event_id: str) -> bool:
    if not event_id:
        return False
    with _WEBHOOK_SEEN_LOCK:
        if event_id in _WEBHOOK_SEEN:
            return True
        _WEBHOOK_SEEN.add(event_id)
        return False


# ---------- Schemas -------------------------------------------------------


class CheckoutRequest(BaseModel):
    product_slug: str  # premium_monthly | pro_monthly | natal_pdf | yearly_forecast
    success_redirect: Optional[str] = None


class CheckoutResponse(BaseModel):
    url: str
    checkout_id: str


class SubscriptionSummary(BaseModel):
    tier: str
    status: Optional[str] = None
    current_period_end: Optional[datetime] = None
    provider: str = "lemon"
    cancel_at_period_end: bool = False


# ---------- Routes --------------------------------------------------------


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    req: CheckoutRequest,
    user: User = Depends(get_current_user_db),
):
    """Create a Lemon Squeezy hosted checkout URL for the requested product."""
    try:
        result = await lemon_provider.create_checkout(
            product_slug=req.product_slug,
            user_id=str(user.id),
            user_email=user.email or "",
            locale=user.language,
            success_redirect=req.success_redirect,
        )
    except lemon_provider.LemonSqueezyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": str(exc), "code": "billing_unavailable"},
        )
    return CheckoutResponse(url=result.url, checkout_id=result.checkout_id)


@router.get("/me", response_model=SubscriptionSummary)
async def my_subscription(
    user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's current subscription summary."""
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
    )
    subs = result.scalars().all()
    tier = current_tier(user, list(subs))
    if not subs:
        return SubscriptionSummary(tier=tier.value)
    s = subs[0]
    return SubscriptionSummary(
        tier=tier.value,
        status=s.status,
        current_period_end=s.current_period_end,
        provider=s.provider or "lemon",
        cancel_at_period_end=s.cancel_at_period_end,
    )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def lemon_webhook(
    request: Request,
    x_signature: Optional[str] = Header(default=None, alias="X-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """Receive Lemon Squeezy webhook events and sync our DB."""
    body = await request.body()
    if not lemon_provider.verify_webhook_signature(body, x_signature or ""):
        logger.warning("Lemon webhook signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    import json

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )

    event = lemon_provider.parse_webhook(payload)

    if _seen(event.event_id):
        logger.info("Lemon webhook %s already processed (idempotent)", event.event_id)
        return {"status": "duplicate"}

    if not event.user_id:
        logger.warning("Lemon webhook %s lacks user_id custom_data", event.event_name)
        return {"status": "no_user_attribution"}

    # Resolve user.
    from uuid import UUID

    try:
        uid = UUID(event.user_id)
    except ValueError:
        return {"status": "bad_user_id"}

    user_result = await db.execute(select(User).where(User.id == uid))
    user = user_result.scalar_one_or_none()
    if user is None:
        logger.warning("Lemon webhook references unknown user_id=%s", event.user_id)
        return {"status": "unknown_user"}

    tier_name = lemon_provider.tier_for_variant(event.variant_id)

    en = event.event_name

    if en in ("subscription_created", "subscription_updated", "subscription_resumed"):
        # Upsert subscription row.
        existing = await db.execute(
            select(Subscription).where(
                Subscription.lemon_subscription_id == event.subscription_id
            )
        )
        sub = existing.scalar_one_or_none()
        if sub is None:
            sub = Subscription(
                user_id=user.id,
                tier=tier_name,
                plan_id=event.variant_id or "",
                status="active",
                provider="lemon",
                lemon_subscription_id=event.subscription_id,
                lemon_variant_id=event.variant_id,
                lemon_customer_id=event.customer_id,
                current_period_start=datetime.utcnow(),
                current_period_end=_parse_iso(event.renews_at)
                or datetime.utcnow(),
            )
            db.add(sub)
        else:
            sub.tier = tier_name
            sub.status = event.status or "active"
            sub.lemon_variant_id = event.variant_id
            sub.lemon_customer_id = event.customer_id
            sub.current_period_end = (
                _parse_iso(event.renews_at) or sub.current_period_end
            )
        if not user.lemon_customer_id and event.customer_id:
            user.lemon_customer_id = event.customer_id
        await db.commit()
        return {"status": "ok", "tier": tier_name}

    if en in ("subscription_cancelled", "subscription_expired", "subscription_paused"):
        existing = await db.execute(
            select(Subscription).where(
                Subscription.lemon_subscription_id == event.subscription_id
            )
        )
        sub = existing.scalar_one_or_none()
        if sub is not None:
            sub.status = (
                "canceled" if en == "subscription_cancelled" else "expired"
            )
            sub.cancel_at_period_end = True
            await db.commit()
        return {"status": "ok"}

    if en == "order_created":
        # One-time purchase. We don't auto-grant tier; the relevant
        # entitlement (e.g., PDF download) is handled by the product code.
        logger.info(
            "Lemon order_created for user=%s variant=%s",
            event.user_id,
            event.variant_id,
        )
        return {"status": "ok"}

    logger.info("Lemon webhook %s ignored (no handler)", en)
    return {"status": "ignored"}


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        # Lemon returns Z-suffixed ISO; datetime.fromisoformat handles +00:00.
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
