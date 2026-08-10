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

KNOWN LIMITATION — concurrency. `check_chart_entitlement` then
`mark_chart_issued` is a read-then-write, not an atomic compare-and-set. Two
first-chart requests from the same free account, fired inside the window
between them, can each pass the check and each mint a distinct chart before
either marks the flag. This is the SAME non-atomicity `quotas.py` already
documents ("would move to Redis in production for multi-process safety"): the
leak is bounded (a free account gets at most a couple of charts under a
precise race, never unlimited — once the flag commits, further charts are
refused), and closing it properly needs a row lock (`SELECT … FOR UPDATE`) or
an atomic UPDATE against the store, which is deferred with the rest of the
quota layer's production hardening rather than shipped as untested
concurrency code.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

from fastapi import HTTPException, status

from backend.core.config import settings
from backend.services.billing.quotas import QuotaKind, Tier, current_tier

logger = logging.getLogger("oneiro.billing.entitlements")

if TYPE_CHECKING:
    from backend.models.user import User


def account_url() -> str:
    """Where a refusal points the user to manage their plan.

    Relative by default because the portal serves `/account` on this same
    service; an absolute `ACCOUNT_URL` overrides it when the account page
    lives elsewhere (e.g. a separate marketing domain).
    """
    return (settings.ACCOUNT_URL or "").rstrip("/") or "/account"


# Two coordinates this close describe the same birth PLACE for charting
# purposes: 0.1° is ~11 km, which shifts the Ascendant by well under a degree,
# while a geocoder centroid routinely sits more than a kilometre from a
# coordinate the caller typed for the same city.
_SAME_PLACE_TOL_DEG = 0.1


def _lon_delta(a: float, b: float) -> float:
    """Angular distance between two longitudes, correct across the ±180 seam."""
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def same_chart(granted_key: Optional[str], requested_key: str) -> bool:
    """Whether a granted chart key and a requested one denote the same chart.

    Deliberately NOT string equality. The key is `utc|lat|lon`, and the same
    birth in the same city resolves to slightly different coordinates
    depending on how the place was supplied — typed by the caller, or returned
    by the geocoder (whose centroid also moves when its data updates). Exact
    matching turned that into "this is a second chart, pay for it": observed
    live on Запорожье, 47.8388/35.1396 typed against 47.85167/35.11714
    geocoded — 1.4 km apart, and refused.

    The birth INSTANT must still match exactly: a different moment is a
    different chart, full stop. Only the place is compared with tolerance.
    """
    if not granted_key:
        return False
    if granted_key == requested_key:
        return True

    granted = granted_key.split("|")
    requested = requested_key.split("|")
    if len(granted) != 3 or len(requested) != 3 or granted[0] != requested[0]:
        return False
    try:
        return (
            abs(float(granted[1]) - float(requested[1])) <= _SAME_PLACE_TOL_DEG
            and _lon_delta(float(granted[2]), float(requested[2])) <= _SAME_PLACE_TOL_DEG
        )
    except ValueError:
        # An unparseable stored key predates this format; exact match already
        # failed above, so treat it as a different chart rather than guessing.
        return False


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


def verification_unavailable_detail(locale: str = "en") -> dict[str, Any]:
    """Refusal body for "we could not verify entitlement" (fail-closed).

    Used when a metered transport reaches the gate but cannot check the
    account — the MCP principal handoff broke, or the entitlement store is
    unreachable. Refusing is safer than issuing an unmetered paid
    computation; the caller should retry. Factual, not promotional.
    """
    return {
        "error": "entitlement_unverifiable",
        "message": (
            "Не удалось проверить права этого аккаунта на запрос. "
            "Повторите попытку; если повторяется — сервис временно не может "
            "проверить ваш тариф."
            if locale == "ru"
            else "Could not verify this account's entitlement for the request. "
            "Please retry; if it persists, the service is temporarily unable "
            "to check your plan."
        ),
        "account_url": account_url(),
    }


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


def check_chart_entitlement(
    user: User,
    chart_key: str,
    *,
    active_subs: Optional[list] = None,
    locale: str = "en",
) -> None:
    """Raise if this account may not be issued the chart identified by `chart_key`.

    Premium and Pro are never gated. A free account may be issued its one
    granted chart any number of times (same `chart_key`), and no other.
    Does not mutate the user — call `mark_chart_issued` after a successful
    issuance to record the grant.

    `active_subs`, when given, is used instead of reading `user.subscriptions`.
    Callers inside an async request should pass it: this function is
    synchronous, so an unloaded relationship read here would emit a lazy SELECT
    from sync code and raise "greenlet_spawn has not been called".
    """
    if current_tier(user, active_subs=active_subs) in (Tier.PREMIUM, Tier.PRO):
        return

    already_used = bool(getattr(user, "free_natal_used", False))
    if not already_used:
        return  # First chart on this account — always allowed.

    granted_key = getattr(user, "free_natal_chart_key", None)
    if same_chart(granted_key, chart_key):
        return  # Re-issuing the account's own chart — free, forever.

    if not granted_key:
        # The flag is set but no key was ever recorded. This is not a state
        # this module's writer produces — it is what the DATABASE contains for
        # every account that burned its grant under the legacy path
        # (`quotas.mark_used` set `free_natal_used` before the key column
        # existed; migration 0002 added the column as NULL). An earlier
        # version of this code refused here as "the safe reading", and the
        # owner hit the consequence live: their own birth data answered
        # `entitlement_required` on every spelling of the city, because a
        # grant with no key can match nothing — the promise "your own chart
        # stays available forever" had quietly become "no chart, ever".
        #
        # A grant we cannot compare is a grant, not a wall. Allow this
        # issuance and let `mark_chart_issued` adopt it as THE granted chart;
        # from then on the account is keyed normally and a second, different
        # chart is refused. Worst case, a grandfathered account whose first
        # chart we cannot identify gets one chart of its choosing — which is
        # exactly what it was promised.
        logger.warning(
            "entitlement: account %s has free_natal_used with no chart key "
            "(legacy grant) — allowing issuance of %s and adopting it as the "
            "grant",
            getattr(user, "id", "?"), chart_key,
        )
        return

    raise EntitlementRequired(
        reason="free_natal_chart_used",
        message=(
            "Бесплатная натальная карта этого аккаунта уже выдана. "
            "Своя карта остаётся доступной; другая карта входит в Premium."
            if locale == "ru"
            else "This account's free natal chart has already been issued. "
            "Its own chart remains available; a different chart is included "
            "with Premium."
        ),
        allowance={"kind": QuotaKind.NATAL_CHART.value, "free": 1, "period": "lifetime"},
        reset_at=None,  # Lifetime — it does not reset.
        tier_required=Tier.PREMIUM.value,
    )


def mark_chart_issued(
    user: User, chart_key: str, *, active_subs: Optional[list] = None
) -> bool:
    """Record that a free account has now been granted `chart_key`.

    Idempotent and free-tier-only: premium/pro accounts have no flag to set,
    and a free account keeps the FIRST chart it was granted (re-issuing that
    chart must not overwrite the grant). Returns True when it changed state,
    so the caller knows whether a DB commit is needed. The caller owns the
    commit — this function never touches the session.

    `active_subs` — same contract as `check_chart_entitlement`: pass the
    already-loaded list from async callers so no lazy load can fire here.
    """
    if current_tier(user, active_subs=active_subs) in (Tier.PREMIUM, Tier.PRO):
        return False
    if getattr(user, "free_natal_used", False):
        if getattr(user, "free_natal_chart_key", None):
            return False
        # Legacy grant (flag without key — see check_chart_entitlement):
        # adopt the chart being issued right now as the granted one, so the
        # account leaves the unkeyed state the moment it is next used.
        user.free_natal_chart_key = chart_key
        return True
    user.free_natal_used = True
    user.free_natal_chart_key = chart_key
    return True
