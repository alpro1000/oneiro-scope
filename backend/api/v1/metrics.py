"""`/api/v1/metrics` — anonymous funnel counters, first-party only.

Why this exists at all: without it, a month from now "the funnel does not
work" and "there is no traffic" look identical, and the face-reading entrance
was built specifically to be measured.

Why it looks this small: the alternative was a third-party analytics script
(GA, Plausible, anything), and that would have cost three things this product
is not willing to spend — a transfer of visitor data to another company, a
new section in the privacy policy (for GA, also the transfer-outside-the-EU
conversation), and an external domain on a frontend that deliberately loads
nothing from anywhere. For four conversion ratios that trade is absurd.

So: the browser POSTs an event NAME from a closed list, plus one boolean it
computed locally. No identifier is sent, none is derived, none is stored. The
endpoint never reads the client's IP, and there is no column that could hold
one. See `backend/models/funnel_counter.py` for the whole schema — it is two
integers keyed by (event, day).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.auth import require_account
from backend.core.database import get_db
from backend.models.user import User
from backend.services.billing.quotas import is_staff
from backend.services.metrics.funnel import FUNNEL_EVENTS, funnel_report, record

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


class EventIn(BaseModel):
    """One anonymous occurrence.

    Note what is absent and cannot be added by a caller: there is no user
    field, no session field, and no free-form payload. `model_config` forbids
    extras, so a client that tries to attach an identifier gets a 422 rather
    than having it silently ignored — the refusal is the point.
    """

    model_config = {"extra": "forbid"}

    event: str = Field(min_length=1, max_length=40)
    returning: bool = Field(
        default=False,
        description=(
            "The browser had been here on an earlier day. Computed on the "
            "device from its own note; the server never learns which visitor."
        ),
    )


class EventOut(BaseModel):
    recorded: bool
    reason: str | None = None


@router.post("/event", response_model=EventOut, status_code=status.HTTP_202_ACCEPTED)
async def post_event(
    body: EventIn, db: AsyncSession = Depends(get_db)
) -> EventOut:
    """Record one funnel event. Unknown names are refused, not stored.

    A counter store that is unreachable answers `recorded: false` with the
    reason rather than a 500: analytics must never be able to break the page
    it is measuring. It also must not lie about having recorded something —
    hence the explicit flag instead of an unconditional 202 (conventions.md
    §12, no silent fallbacks).
    """
    if body.event not in FUNNEL_EVENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown event; expected one of {sorted(FUNNEL_EVENTS)}",
        )
    try:
        ok = await record(db, body.event, returning=body.returning)
    except Exception as exc:  # noqa: BLE001 — never break the page being measured
        logger.warning("funnel counter unavailable: %s: %s", type(exc).__name__, exc)
        return EventOut(recorded=False, reason="counter store unavailable")
    return EventOut(recorded=ok)


@router.get("/funnel")
async def get_funnel(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(require_account),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """The four ratios. Staff only — business numbers, not public ones.

    Nothing here is personal data, so the gate is about not publishing the
    product's performance rather than about protecting anybody.
    """
    if not is_staff(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="staff only"
        )
    return await funnel_report(db, days=days)
