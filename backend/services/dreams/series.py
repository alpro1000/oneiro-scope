"""Personal dream series: store coded dreams, compare a user to themself.

The Hall/Van de Castle norms are a 1947–1950 college sample — fine as a
research reference, weak as a personal mirror. Methodologically cleaner
(Domhoff's long individual series) is comparing today's dream against the
user's OWN accumulated baseline. This module stores the deterministic
coding output per dream (never the text) and computes series statistics.

Honesty rule: below MIN_SERIES_N coded dreams the series is too short for
baseline talk — the stats call says so explicitly instead of producing
means of three data points.
"""

from __future__ import annotations

import logging
import statistics
import uuid as uuid_mod
from datetime import date, timedelta
from typing import Any, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.dream import DreamEntry
from backend.services.dreams.hvdc_coder import HVDC_CODER_VERSION
from backend.services.dreams.schemas import ContentAnalysis

logger = logging.getLogger(__name__)

# Domhoff works with series of dozens to hundreds of dreams; 15 is the
# explicit floor below which we refuse to call anything a baseline.
MIN_SERIES_N = 15

SERIES_FIELDS = [
    "male_characters", "female_characters", "animal_characters",
    "friendly_interactions", "aggressive_interactions", "sexual_interactions",
    "successes", "failures", "misfortunes", "good_fortunes",
]

PERIODS: dict[str, Optional[int]] = {
    "30d": 30,
    "90d": 90,
    "365d": 365,
    "all": None,
}


async def store_entry(
    session: AsyncSession,
    *,
    user_id: uuid_mod.UUID,
    dream_date: date,
    locale: str,
    content: ContentAnalysis,
    symbols: List[str],
    primary_emotion: Optional[str],
) -> DreamEntry:
    entry = DreamEntry(
        user_id=user_id,
        dream_date=dream_date,
        locale=locale,
        coder_version=HVDC_CODER_VERSION,
        hvdc={f: getattr(content, f) for f in SERIES_FIELDS},
        symbols=symbols,
        primary_emotion=primary_emotion,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def series_stats(
    session: AsyncSession,
    user_id: uuid_mod.UUID,
    period: str = "all",
) -> dict[str, Any]:
    """Per-indicator personal baseline, trend, and the latest dream's
    deviation from the user's own series."""
    if period not in PERIODS:
        raise ValueError(f"period must be one of {sorted(PERIODS)}")

    query = select(DreamEntry).where(DreamEntry.user_id == user_id)
    days = PERIODS[period]
    if days is not None:
        query = query.where(DreamEntry.dream_date >= date.today() - timedelta(days=days))
    query = query.order_by(DreamEntry.dream_date)

    entries = list((await session.execute(query)).scalars())
    n = len(entries)

    out: dict[str, Any] = {
        "user_id": str(user_id),
        "period": period,
        "n": n,
        "min_required": MIN_SERIES_N,
        "coder_versions": sorted({e.coder_version for e in entries}),
        "source": (
            "Personal dream series, deterministic HVdC coding. Approach: "
            "Domhoff (1996), individual dream series."
        ),
    }

    if n < MIN_SERIES_N:
        out["status"] = "insufficient_data"
        out["message_ru"] = (
            f"В серии {n} закодированных снов — для личной базовой линии "
            f"нужно минимум {MIN_SERIES_N}. Продолжайте записывать сны; "
            "пока доступно только сравнение с нормами Hall/Van de Castle."
        )
        out["message_en"] = (
            f"The series holds {n} coded dreams — a personal baseline needs "
            f"at least {MIN_SERIES_N}. Keep journaling; until then only the "
            "Hall/Van de Castle norm comparison is available."
        )
        return out

    out["status"] = "ok"

    values = {f: [int(e.hvdc.get(f, 0)) for e in entries] for f in SERIES_FIELDS}
    baseline = {}
    for f in SERIES_FIELDS:
        mean = statistics.fmean(values[f])
        std = statistics.pstdev(values[f])
        baseline[f] = {"mean": round(mean, 3), "std": round(std, 3)}
    out["baseline"] = baseline

    # Trend: first half vs second half of the (date-ordered) series.
    half = n // 2
    trend = {}
    for f in SERIES_FIELDS:
        first = statistics.fmean(values[f][:half])
        second = statistics.fmean(values[f][half:])
        direction = "up" if second > first else "down" if second < first else "flat"
        trend[f] = {
            "first_half_mean": round(first, 3),
            "second_half_mean": round(second, 3),
            "direction": direction,
        }
    out["trend"] = trend

    latest = entries[-1]
    deviations = {}
    for f in SERIES_FIELDS:
        value = int(latest.hvdc.get(f, 0))
        mean = baseline[f]["mean"]
        std = baseline[f]["std"]
        item: dict[str, Any] = {
            "value": value,
            "personal_mean": mean,
            "delta": round(value - mean, 3),
        }
        if std > 0:
            z = (value - mean) / std
            item["z"] = round(z, 2)
            item["notable"] = abs(z) >= 2
        else:
            # Нулевой разброс: любое отличие — новизна, z не определён.
            item["z"] = None
            item["notable"] = value != mean
        deviations[f] = item
    out["latest"] = {
        "dream_date": latest.dream_date.isoformat(),
        "deviations": deviations,
    }
    return out


async def export_entries(session: AsyncSession, user_id: uuid_mod.UUID) -> List[dict]:
    """GDPR Article 20 — the user's coded series as plain dicts."""
    entries = (
        await session.execute(
            select(DreamEntry)
            .where(DreamEntry.user_id == user_id)
            .order_by(DreamEntry.dream_date)
        )
    ).scalars()
    return [
        {
            "id": str(e.id),
            "dream_date": e.dream_date.isoformat(),
            "locale": e.locale,
            "coder_version": e.coder_version,
            "hvdc": e.hvdc,
            "symbols": e.symbols,
            "primary_emotion": e.primary_emotion,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


async def delete_entries(session: AsyncSession, user_id: uuid_mod.UUID) -> int:
    """GDPR Article 17 — explicit erase, independent of the user-row cascade."""
    result = await session.execute(
        delete(DreamEntry).where(DreamEntry.user_id == user_id)
    )
    await session.commit()
    return result.rowcount or 0
