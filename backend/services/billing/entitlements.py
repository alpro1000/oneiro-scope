"""The gate on `chart_core` issuance — one seam, every transport.

The owner's design puts the paywall on the ISSUANCE of a chart, not on the
features derived from it. A `chart_core` is ~1.7 KB and, once a client has
it, `packages/chart-kit` computes angles, houses, aspects, the wheel and
astrocartography locally forever. So metering the derived features would be
both futile (they are client-side) and hostile (the user already paid for
the data). The one thing worth metering is the ephemeris computation that
mints the payload — and that is exactly here.

`check_chart_entitlement` is transport-neutral: `POST /api/v1/chart`, the
rich `POST /api/v1/astrology/natal-chart`, and the MCP `calculate_natal_chart`
tool all call it with the same `User`-shaped principal, so the three doors
that can mint a core cannot drift apart or leave a bypass. Anything a `User`
quacks like works (tier from `subscriptions`, the two free-tier flags), which
keeps this testable without a database — the same discipline `quotas.py` uses.

"One chart forever" is taken literally. A free account is granted ONE natal
chart, identified by its birth instant (`chart_core.chart_identity`). Issuing
that same chart again — a page reload, a cleared cache, a second device — is
always free, because the account already owns it. Only a DIFFERENT chart is
refused. A bare "used a free chart" boolean would instead evaporate a user's
single chart the first time they cleared their browser, which is not what
"forever" means.

Refusals are structured and factual, never sales copy: the limit, when it
resets (null = lifetime), the tier that lifts it, and where to manage the
account. No "upgrade now!" — the client decides how to present the fact.
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from fastapi import HTTPException, status

from backend.core.config import settings
from backend.services.billing.quotas import QuotaKind, Tier, current_tier

if TYPE_CHECKING:
    from backend.models.user import User


def account_url() -> str:
    """Where a refusal points the user to manage their plan.

    Relative by default because the portal serves `/account` on this same
    service; an absolute `ACCOUNT_URL` overrides it when the account page
    lives elsewhere (e.g. a separate marketing domain).
    """
    return (settings.ACCOUNT_URL or "").rstrip("/") or "/account"


class EntitlementRequired(HTTPException):
    """A principal asked for a chart their plan does not include.

    An HTTPException so the HTTP transports raise it as-is (FastAPI renders
    the 402 with the structured detail); the MCP transport catches it and
    returns `detail` as a plain dict. One refusal shape, both doors.
    """

    def __init__(
        self,
        *,
        reason: str,
        message: str,
        allowance: dict[str, Any],
        reset_at: Optional[str],
        tier_required: str,
    ) -> None:
        detail = {
            "error": "entitlement_required",
            "reason": reason,
            # Factual, not promotional — states what is true, not what to buy.
            "message": message,
            "allowance": allowance,
            # null for a lifetime allowance; an ISO instant for a periodic one
            # (daily quotas, once they route through here) so the client can
            # say "resets at …" without inventing the time.
            "reset_at": reset_at,
            "tier_required": tier_required,
            "account_url": account_url(),
        }
        super().__init__(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)
        self.reason = reason


class AccountRequired(HTTPException):
    """A chart was requested with no account to attribute it to.

    "One chart forever" is a promise about an account; there is nothing to
    keep the promise against without one. This is a 401 (not 403) with the
    same structured shape and a `WWW-Authenticate` header, so a client knows
    it must authenticate rather than that it is forbidden outright.
    """

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "account_required",
                "message": message,
                "account_url": account_url(),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_chart_entitlement(user: User, chart_key: str) -> None:
    """Raise if this account may not be issued the chart identified by `chart_key`.

    Premium and Pro are never gated. A free account may be issued its one
    granted chart any number of times (same `chart_key`), and no other.
    Does not mutate the user — call `mark_chart_issued` after a successful
    issuance to record the grant.
    """
    if current_tier(user) in (Tier.PREMIUM, Tier.PRO):
        return

    already_used = bool(getattr(user, "free_natal_used", False))
    if not already_used:
        return  # First chart on this account — always allowed.

    granted_key = getattr(user, "free_natal_chart_key", None)
    if granted_key is not None and granted_key == chart_key:
        return  # Re-issuing the account's own chart — free, forever.

    raise EntitlementRequired(
        reason="free_natal_chart_used",
        message=(
            "This account's free natal chart has already been issued. "
            "Its own chart remains available; a different chart is included "
            "with Premium."
        ),
        allowance={"kind": QuotaKind.NATAL_CHART.value, "free": 1, "period": "lifetime"},
        reset_at=None,  # Lifetime — it does not reset.
        tier_required=Tier.PREMIUM.value,
    )


def mark_chart_issued(user: User, chart_key: str) -> bool:
    """Record that a free account has now been granted `chart_key`.

    Idempotent and free-tier-only: premium/pro accounts have no flag to set,
    and a free account keeps the FIRST chart it was granted (re-issuing that
    chart must not overwrite the grant). Returns True when it changed state,
    so the caller knows whether a DB commit is needed. The caller owns the
    commit — this function never touches the session.
    """
    if current_tier(user) in (Tier.PREMIUM, Tier.PRO):
        return False
    if getattr(user, "free_natal_used", False):
        return False
    user.free_natal_used = True
    user.free_natal_chart_key = chart_key
    return True
