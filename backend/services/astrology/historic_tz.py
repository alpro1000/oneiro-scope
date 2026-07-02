"""Historic birth-time resolution: local clock → UTC → Julian Day.

Every chart in the pipeline starts with "born 1977-07-01 22:30 in
Zaporizhzhia". Getting the UTC offset wrong by an hour moves every
house cusp and angle — the most common user error in relocation
astrology. This module resolves it deterministically:

- Timezone name is derived from birth coordinates (timezonefinder),
  or taken explicitly.
- The IANA tz database applied via `zoneinfo` carries *historical*
  rules — Soviet decree time, DST changes, zone splits — accurately
  back to ~1970 and reasonably before.
- Output includes provenance: resolved zone, UTC offset actually used,
  and a `pre_1970` flag when tzdata precision degrades.

Pure computation — ASTRONOMY layer input.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls, datetime, time as time_cls, timezone
from typing import Optional
from zoneinfo import ZoneInfo

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover
    raise ImportError("pyswisseph is required for birth-moment resolution") from exc

try:
    from timezonefinder import TimezoneFinder
except ImportError:  # pragma: no cover - optional at import time
    TimezoneFinder = None  # type: ignore[assignment]

_tf: Optional["TimezoneFinder"] = None


def _finder() -> Optional["TimezoneFinder"]:
    global _tf
    if _tf is None and TimezoneFinder is not None:
        _tf = TimezoneFinder()
    return _tf


@dataclass(frozen=True)
class BirthMoment:
    """Resolved birth moment with provenance."""

    jd_ut: float
    utc_iso: str
    timezone_name: str
    utc_offset_hours: float
    pre_1970: bool  # tzdata rules are less reliable before ~1970
    source: str  # "explicit" | "coordinates" | "fallback-utc"


def timezone_for(lat: float, lon: float) -> Optional[str]:
    """IANA timezone name for coordinates, or None if unresolvable."""
    tf = _finder()
    if tf is None:
        return None
    return tf.timezone_at(lat=lat, lng=lon)


def resolve_birth_moment(
    birth_date: date_cls,
    birth_time: Optional[time_cls],
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    timezone_name: Optional[str] = None,
) -> BirthMoment:
    """Resolve a local birth date/time into a Julian Day (UT).

    Priority: explicit `timezone_name` → coordinates lookup → UTC
    fallback. Historical offsets (Soviet decree time, DST) come from
    the IANA database via zoneinfo. Raises ValueError for an unknown
    explicit timezone — never silently substitutes UTC for a bad name.
    """
    t = birth_time or time_cls(12, 0)

    if timezone_name:
        try:
            tz = ZoneInfo(timezone_name)
        except Exception as exc:
            raise ValueError(
                f"Invalid timezone: {timezone_name!r}. "
                "Use an IANA name like 'Europe/Kyiv' or 'UTC'."
            ) from exc
        source = "explicit"
        zone_label = timezone_name
    elif lat is not None and lon is not None:
        zone = timezone_for(lat, lon)
        if zone:
            tz = ZoneInfo(zone)
            source = "coordinates"
            zone_label = zone
        else:
            tz = ZoneInfo("UTC")
            source = "fallback-utc"
            zone_label = "UTC"
    else:
        tz = ZoneInfo("UTC")
        source = "fallback-utc"
        zone_label = "UTC"

    local = datetime(
        birth_date.year, birth_date.month, birth_date.day,
        t.hour, t.minute, getattr(t, "second", 0), tzinfo=tz,
    )
    utc = local.astimezone(timezone.utc)
    offset = local.utcoffset()
    offset_hours = (offset.total_seconds() / 3600.0) if offset else 0.0

    jd = swe.julday(
        utc.year, utc.month, utc.day,
        utc.hour + utc.minute / 60.0 + utc.second / 3600.0,
    )
    return BirthMoment(
        jd_ut=jd,
        utc_iso=utc.isoformat(),
        timezone_name=zone_label,
        utc_offset_hours=round(offset_hours, 2),
        pre_1970=birth_date.year < 1970,
        source=source,
    )
