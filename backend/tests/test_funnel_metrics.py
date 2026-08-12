"""The funnel counters, and the promises they must not break.

Most of this file tests ABSENCES. That is deliberate: the reason this
analytics exists at all instead of a third-party script is a privacy claim,
and a privacy claim is only as good as the thing that fails when someone
quietly adds a user id "just for cohorts". So the schema, the request model
and the emitted payload are all pinned against identifiers.
"""

from __future__ import annotations

import datetime as _dt

import asyncio

import pytest

from backend.services.metrics.funnel import FUNNEL_EVENTS, funnel_report, record

sa = pytest.importorskip("sqlalchemy", reason="sqlalchemy not installed")

from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession, async_sessionmaker, create_async_engine,
)

from backend.core.database import Base  # noqa: E402
from backend.models.funnel_counter import FunnelCounter  # noqa: E402


@pytest.fixture
def run():
    """Run one async body against a fresh in-memory store.

    Engine, schema, session and body all live inside a SINGLE `asyncio.run`,
    and that is load-bearing rather than tidy. An engine created on one event
    loop and used on another does not raise — the aiosqlite driver simply
    waits forever on a connection bound to a dead loop, so the test hangs
    instead of failing. Building everything inside the loop that uses it
    removes the possibility.
    """
    pytest.importorskip("aiosqlite", reason="aiosqlite not installed")

    def _run(body):
        """`body` takes a session and returns whatever the test wants."""
        async def _wrapped():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(FunnelCounter.__table__.create)
                maker = async_sessionmaker(
                    engine, class_=AsyncSession, expire_on_commit=False
                )
                async with maker() as s:
                    return await body(s)
            finally:
                await engine.dispose()

        return asyncio.run(_wrapped())

    return _run


# --- the privacy claim, as structure -----------------------------------------


def test_the_table_has_no_column_that_could_identify_anyone():
    """The strongest form of "we do not store identifiers": there is nowhere
    to put one. If a future change adds a user, session, device or address
    column, this fails before any of it reaches a migration."""
    columns = set(FunnelCounter.__table__.columns.keys())
    assert columns == {"event", "day", "total", "returning_count", "updated_at"}, columns
    forbidden = ("user", "session", "device", "ip", "addr", "client",
                 "fingerprint", "visitor", "uid", "token")
    for col in columns:
        for word in forbidden:
            assert word not in col.lower(), f"{col} smells like an identifier"


def test_the_day_column_is_a_date_not_a_timestamp():
    """A timestamp per event starts describing individual visits — at low
    traffic, a precise time IS close to an identifier. A calendar day is the
    coarsest bucket that still answers the owner's questions."""
    assert isinstance(FunnelCounter.__table__.c.day.type, sa.Date)
    assert not isinstance(FunnelCounter.__table__.c.day.type, sa.DateTime)


def test_the_request_model_refuses_extra_fields():
    """A client attaching an identifier must be REFUSED, not silently
    ignored: silently dropping it would leave the caller believing it was
    accepted, and the next person to read the code would add a column."""
    from pydantic import ValidationError

    from backend.api.v1.metrics import EventIn

    with pytest.raises(ValidationError):
        EventIn(event="face_result_shown", user_id="abc")  # type: ignore[call-arg]

    assert set(EventIn.model_fields) == {"event", "returning"}


# --- behaviour ----------------------------------------------------------------


def test_an_unknown_event_is_refused_not_recorded(run):
    """An open endpoint that creates a row per arbitrary string is a way to
    fill someone's database from a browser."""
    async def body(s):
        refused = await record(s, "definitely_not_an_event")
        rows = (await s.execute(sa.select(FunnelCounter))).scalars().all()
        return refused, rows

    refused, rows = run(body)
    assert refused is False
    assert rows == []


def test_counts_accumulate_per_event_and_day(run):
    day = _dt.date(2026, 8, 3)

    async def body(s):
        for _ in range(3):
            await record(s, "face_result_shown", today=day)
        await record(s, "face_result_shown", returning=True, today=day)
        await record(s, "face_result_shown", today=_dt.date(2026, 8, 4))
        return {
            (r.event, r.day): (r.total, r.returning_count)
            for r in (await s.execute(sa.select(FunnelCounter))).scalars().all()
        }

    rows = run(body)
    assert rows[("face_result_shown", day)] == (4, 1)
    assert rows[("face_result_shown", _dt.date(2026, 8, 4))] == (1, 0)


def test_the_four_ratios_are_computed_over_the_window(run):
    day = _dt.date(2026, 8, 10)

    async def body(s):
        for _ in range(10):
            await record(s, "face_result_shown", today=day)
        for _ in range(4):
            await record(s, "birth_date_entered", today=day)
        for _ in range(3):
            await record(s, "natal_computed", today=day)
        return await funnel_report(s, days=7, today=day)

    rep = run(body)
    r = rep["ratios"]
    assert r["entered_date_of_those_who_saw_a_result"] == 0.4
    assert r["computed_chart_of_those_who_entered"] == 0.75
    assert rep["totals"]["face_result_shown"] == 10


def test_a_ratio_with_no_denominator_is_none_not_zero(run):
    """Same rule as the dream norms: "nobody got there yet" and "everyone who
    got there dropped out" are opposite findings. Rendering both as 0.00 is
    how a dashboard tells its owner a comforting lie."""
    rep = run(lambda s: funnel_report(s, days=30, today=_dt.date(2026, 8, 10)))
    for name, value in rep["ratios"].items():
        assert value is None, f"{name} invented a ratio out of no data"


def test_days_outside_the_window_are_excluded(run):
    old, now = _dt.date(2026, 7, 1), _dt.date(2026, 8, 10)

    async def body(s):
        await record(s, "face_result_shown", today=old)
        await record(s, "face_result_shown", today=now)
        return await funnel_report(s, days=7, today=now)

    assert run(body)["totals"]["face_result_shown"] == 1


def test_the_report_says_the_numbers_are_not_forgery_proof(run):
    """Anonymous client-side counters cannot be audited — anyone can POST an
    event. Reading them as a ledger would be a mistake, so the report says so
    where it is read rather than in a document nobody opens."""
    rep = run(lambda s: funnel_report(s, days=1, today=_dt.date(2026, 8, 10)))
    assert "not" in rep["note"].lower()
    assert "trend" in rep["note"].lower()


def test_the_event_list_is_the_one_the_privacy_policy_describes():
    """Adding a sixth event is a decision about what the product measures,
    and the privacy policy quotes this list. Changing it here without
    changing that text is the drift this test exists to stop."""
    assert FUNNEL_EVENTS == {
        "face_result_shown",
        "birth_date_entered",
        "natal_computed",
        "share_clicked",
        "dream_analyzed",
    }
