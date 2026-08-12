"""The four numbers that tell whether the face-reading funnel works.

Scope is deliberately tiny. There are five event names and no others, and a
sixth would be a decision, not a convenience — every name here is a promise
about what the product measures, and the privacy policy quotes that promise.

The four ratios the owner asked for, and how they are computed:

  reached_result    face_result_shown                     — denominator
  entered_date      birth_date_entered / face_result_shown — THE conversion
  computed_chart    natal_computed     / birth_date_entered
  returned          returning / total on face_result_shown — does the hand-off
                                                             to transits work
  shared            share_clicked      / face_result_shown

Measure from day one or a month from now you cannot tell "the funnel is
broken" from "there is no traffic" — which is exactly the state this module
exists to prevent.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.funnel_counter import FunnelCounter

#: The closed list. An unknown name is rejected, never recorded: an open
#: endpoint that creates a row per string is a way to fill someone's database
#: from a browser, and an event nobody defined is not a measurement anyway.
FUNNEL_EVENTS: frozenset[str] = frozenset({
    "face_result_shown",    # a complete reading rendered — the denominator
    "birth_date_entered",   # the hand-off form was submitted
    "natal_computed",       # the chart actually came back
    "share_clicked",        # DECLARED, NOT YET FIRED: the share image is not
                            # built. Named now so the allow-list stays stable
                            # and the first share does not need a migration.
    "dream_analyzed",       # the other entrance, for the same denominator work
})


async def record(
    session: AsyncSession,
    event: str,
    *,
    returning: bool = False,
    today: _dt.date | None = None,
) -> bool:
    """Increment one counter. Returns False if the event name is unknown.

    Deliberately not an upsert-with-ON-CONFLICT one-liner: this runs on
    SQLite in tests and Postgres in production, and the dialect-specific
    upserts differ. Read-then-write is safe here because losing a count in a
    race costs nothing — these are trend counters, not money.
    """
    if event not in FUNNEL_EVENTS:
        return False

    day = today or _dt.datetime.now(_dt.timezone.utc).date()
    row = await session.get(FunnelCounter, (event, day))
    if row is None:
        row = FunnelCounter(event=event, day=day, total=0, returning_count=0)
        session.add(row)
    row.total = (row.total or 0) + 1
    if returning:
        row.returning_count = (row.returning_count or 0) + 1
    await session.commit()
    return True


async def funnel_report(
    session: AsyncSession, days: int = 30, today: _dt.date | None = None
) -> dict[str, Any]:
    """Totals per event over a window, plus the ratios that matter.

    A ratio whose denominator is zero comes back as None, not 0.0 — the same
    rule the dream norms follow. "Nobody reached the result yet" and "everyone
    who reached it dropped out" are opposite findings and must not render as
    the same number.
    """
    end = today or _dt.datetime.now(_dt.timezone.utc).date()
    start = end - _dt.timedelta(days=max(days, 1) - 1)

    rows = (await session.execute(
        select(FunnelCounter).where(
            FunnelCounter.day >= start, FunnelCounter.day <= end
        )
    )).scalars().all()

    totals: dict[str, int] = {e: 0 for e in sorted(FUNNEL_EVENTS)}
    returning: dict[str, int] = {e: 0 for e in sorted(FUNNEL_EVENTS)}
    for r in rows:
        totals[r.event] = totals.get(r.event, 0) + int(r.total or 0)
        returning[r.event] = returning.get(r.event, 0) + int(r.returning_count or 0)

    def ratio(top: str, bottom: str) -> float | None:
        denom = totals.get(bottom, 0)
        return round(totals.get(top, 0) / denom, 4) if denom else None

    shown = totals.get("face_result_shown", 0)
    return {
        "window": {"from": start.isoformat(), "to": end.isoformat(), "days": days},
        "totals": totals,
        "ratios": {
            # The conversion of the whole funnel: a finished free reading, and
            # then the person answers with their birth date.
            "entered_date_of_those_who_saw_a_result": ratio(
                "birth_date_entered", "face_result_shown"
            ),
            "computed_chart_of_those_who_entered": ratio(
                "natal_computed", "birth_date_entered"
            ),
            "shared_of_those_who_saw_a_result": ratio(
                "share_clicked", "face_result_shown"
            ),
            # Whether the hand-off to transits gives anyone a reason to come
            # back — the only one of the four that measures the PRODUCT rather
            # than the page.
            "returned_of_those_who_saw_a_result": (
                round(returning.get("face_result_shown", 0) / shown, 4)
                if shown else None
            ),
        },
        "note": (
            "Counts are anonymous and self-reported by browsers: no identifier "
            "is stored and nothing here is forgery-proof. Read them as trends, "
            "not as an audited ledger."
        ),
    }
