"""Personal dream-series service: baseline honesty and GDPR paths.

Runs on in-memory SQLite (the DreamEntry model uses the dialect-agnostic
Uuid type for exactly this reason). Only the dream_entries table is
created — SQLite does not enforce the users FK by default, and the user
row is irrelevant to the statistics under test.
"""

import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.models.dream import DreamEntry
from backend.services.dreams import series
from backend.services.dreams.schemas import ContentAnalysis

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: DreamEntry.__table__.create(sync_conn)
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _content(**overrides) -> ContentAnalysis:
    base = dict(
        male_characters=1, female_characters=1, animal_characters=0,
        friendly_interactions=1, aggressive_interactions=0,
        sexual_interactions=0, successes=0, failures=0,
        misfortunes=0, good_fortunes=0,
    )
    base.update(overrides)
    return ContentAnalysis(**base)


async def _fill(session, user_id, n, start=date(2026, 1, 1), **overrides):
    for i in range(n):
        await series.store_entry(
            session,
            user_id=user_id,
            dream_date=start + timedelta(days=i),
            locale="ru",
            content=_content(**overrides),
            symbols=["water"],
            primary_emotion="neutral",
        )


async def test_below_threshold_is_insufficient_not_a_baseline(session):
    """Задание, часть 4: значимая статистика только с N>=15 — ниже честно
    сообщаем, что выборки недостаточно."""
    user_id = uuid.uuid4()
    await _fill(session, user_id, series.MIN_SERIES_N - 1)
    out = await series.series_stats(session, user_id)
    assert out["status"] == "insufficient_data"
    assert out["n"] == series.MIN_SERIES_N - 1
    assert out["min_required"] == series.MIN_SERIES_N
    assert "baseline" not in out
    assert out["message_ru"] and out["message_en"]


async def test_threshold_is_explicit_and_at_least_15():
    assert series.MIN_SERIES_N >= 15


async def test_exact_threshold_boundary_computes_full_stats(session):
    """n == MIN_SERIES_N ровно: baseline и тренд считаются, обе половины
    непусты (7+8), краша нет — регрессионная броня против ложного
    ревью-срабатывания на PR #166."""
    user_id = uuid.uuid4()
    await _fill(session, user_id, series.MIN_SERIES_N)
    out = await series.series_stats(session, user_id)
    assert out["status"] == "ok"
    assert out["n"] == series.MIN_SERIES_N
    trend = out["trend"]["friendly_interactions"]
    assert trend["first_half_mean"] == 1.0 and trend["second_half_mean"] == 1.0
    assert trend["direction"] == "flat"


async def test_full_series_baseline_trend_and_deviation(session):
    user_id = uuid.uuid4()
    # 15 calm dreams, then one aggressive outlier.
    await _fill(session, user_id, 15)
    await series.store_entry(
        session,
        user_id=user_id,
        dream_date=date(2026, 2, 1),
        locale="ru",
        content=_content(aggressive_interactions=4, friendly_interactions=0),
        symbols=["war"],
        primary_emotion="anger",
    )
    out = await series.series_stats(session, user_id)
    assert out["status"] == "ok"
    assert out["n"] == 16
    assert out["baseline"]["friendly_interactions"]["mean"] == pytest.approx(15 / 16, abs=0.01)
    latest = out["latest"]["deviations"]["aggressive_interactions"]
    assert latest["value"] == 4
    assert latest["notable"] is True
    assert out["trend"]["aggressive_interactions"]["direction"] == "up"


async def test_period_filter_and_unknown_period(session):
    user_id = uuid.uuid4()
    await _fill(session, user_id, 20, start=date(2020, 1, 1))  # far past
    out = await series.series_stats(session, user_id, period="90d")
    assert out["n"] == 0
    assert out["status"] == "insufficient_data"
    with pytest.raises(ValueError):
        await series.series_stats(session, user_id, period="week")


async def test_gdpr_export_and_delete(session):
    """Задание, часть 4: экспорт и удаление по GDPR."""
    user_id = uuid.uuid4()
    other = uuid.uuid4()
    await _fill(session, user_id, 3)
    await _fill(session, other, 2)

    exported = await series.export_entries(session, user_id)
    assert len(exported) == 3
    assert exported[0]["hvdc"]["friendly_interactions"] == 1
    assert "dream_text" not in exported[0], "series must never hold texts"

    deleted = await series.delete_entries(session, user_id)
    assert deleted == 3
    assert await series.export_entries(session, user_id) == []
    # Чужая серия не тронута.
    assert len(await series.export_entries(session, other)) == 2


async def test_series_tools_take_no_user_argument_at_all():
    """The series is the CALLER's, and there is nothing to point elsewhere.

    Both tools used to accept a `user_id` / `store_for_user_id` UUID straight
    off the tool call, with nothing verifying the caller owned it — so anyone
    who learned another person's UUID could read and append to their dream
    journal. The fix is structural rather than a validation check: no
    parameter names a user, so no argument can be forged.
    """
    import inspect

    from backend.mcp.tools.dreams import analyze_dream, dream_series_stats

    stats_params = set(inspect.signature(dream_series_stats).parameters)
    assert "user_id" not in stats_params, stats_params

    analyze_params = set(inspect.signature(analyze_dream).parameters)
    assert "store_for_user_id" not in analyze_params, analyze_params
    # Journalling stays opt-in — it just consents for yourself now.
    assert "remember" in analyze_params


async def test_series_stats_refuses_without_an_authenticated_caller():
    """No principal, no series — never a silent read of somebody's data."""
    from backend.mcp.tools.dreams import dream_series_stats

    # No MCP request in context here, so there is no authenticated subject.
    out = await dream_series_stats()
    assert out["status"] in {"sign_in_required", "no_connector_account"}
    assert "error" in out


async def test_storing_refuses_without_an_authenticated_caller():
    """`remember=True` off an authenticated transport must not guess an owner."""
    from backend.mcp.tools.dreams import _store_in_series

    out = await _store_in_series(
        _FakeAnalysis(),
        dream_date=date(2026, 1, 1),
        locale="en",
    )
    assert out["stored"] is False
    assert out["reason"] in {"sign_in_required", "no_connector_account"}


class _FakeAnalysis:
    """Enough of a DreamAnalysisResponse for the storage path's early exit."""

    content_analysis = None
    symbols: list = []
    primary_emotion = None
