"""Transit search — compute exact dates over a period.

For a natal chart and a window, finds when each transiting planet forms
a major aspect (0/60/90/120/180°) to a natal planet, within a configurable
orb. Returns sorted, deduplicated event list.

This is pure astronomy — output goes into the Strategic Layer as
`Layer.ASTRONOMY` evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover
    raise ImportError("pyswisseph is required for transit search") from exc

_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

# Transiting planets we scan. Slow planets dominate — fast planets like
# Moon are too noisy to be useful here.
_TRANSITING = [
    (swe.MARS, "Mars"),
    (swe.JUPITER, "Jupiter"),
    (swe.SATURN, "Saturn"),
    (swe.URANUS, "Uranus"),
    (swe.NEPTUNE, "Neptune"),
    (swe.PLUTO, "Pluto"),
    # Chiron intentionally excluded — requires .se1 asteroid files
    # (seas_18.se1). MOSEPH doesn't ship asteroids. Add back when
    # SE_EPHE_PATH binaries are bundled in deploy.
]

_NATAL_BODIES = [
    (swe.SUN, "Sun"),
    (swe.MOON, "Moon"),
    (swe.MERCURY, "Mercury"),
    (swe.VENUS, "Venus"),
    (swe.MARS, "Mars"),
    (swe.JUPITER, "Jupiter"),
    (swe.SATURN, "Saturn"),
]

_ASPECTS = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}


@dataclass(frozen=True)
class TransitEvent:
    transiting: str
    aspect: str
    natal: str
    exact_date: str  # YYYY-MM-DD
    orb_at_midnight: float


def _angle_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360
    if d > 180:
        d = 360 - d
    return d


def _aspect_orb(a: float, b: float, aspect_deg: float) -> float:
    """Smallest orb to a given aspect angle (0/60/90/120/180)."""
    return abs(_angle_diff(a, b) - aspect_deg)


def find_transits(
    natal_jd_ut: float,
    start: date,
    end: date,
    *,
    orb_deg: float = 3.0,
) -> list[TransitEvent]:
    """Return all (transiting × natal × aspect) exact-dates between
    `start` and `end` (inclusive) where the orb at noon-UT goes below
    `orb_deg` at any point.

    Algorithm: scan daily; when current orb minimum < threshold AND
    previous orb was bigger, treat the local minimum as "exact". Naive
    but accurate to ~1 day, which is what users care about.
    """
    natal: dict[str, float] = {}
    for code, name in _NATAL_BODIES:
        natal[name] = swe.calc_ut(natal_jd_ut, code, _FLAGS)[0][0]

    events: list[TransitEvent] = []

    for tcode, tname in _TRANSITING:
        # Build daily series of (date, transit longitude).
        cur = start
        # Track per (aspect × natal) the previous orb.
        prev_orb: dict[tuple[str, str], float] = {}

        while cur <= end:
            jd = swe.julday(cur.year, cur.month, cur.day, 12.0)
            tlon = swe.calc_ut(jd, tcode, _FLAGS)[0][0]

            for nname, nlon in natal.items():
                for aname, adeg in _ASPECTS.items():
                    orb = _aspect_orb(tlon, nlon, adeg)
                    key = (aname, nname)
                    prev = prev_orb.get(key, 999.0)

                    # Detect local minimum below threshold: orb was
                    # bigger yesterday, now under threshold, and
                    # smaller than the noise floor.
                    if orb <= orb_deg and prev > orb and orb < 5.0:
                        # Probe ±1 day to confirm minimum.
                        next_jd = jd + 1.0
                        next_lon = swe.calc_ut(next_jd, tcode, _FLAGS)[0][0]
                        next_orb = _aspect_orb(next_lon, nlon, adeg)
                        if orb <= next_orb:
                            # Local minimum confirmed.
                            events.append(
                                TransitEvent(
                                    transiting=tname,
                                    aspect=aname,
                                    natal=nname,
                                    exact_date=cur.isoformat(),
                                    orb_at_midnight=round(orb, 2),
                                )
                            )
                    prev_orb[key] = orb
            cur += timedelta(days=1)

    # Deduplicate (same transit × aspect × natal × date may double-report)
    seen = set()
    deduped = []
    for e in events:
        key = (e.transiting, e.aspect, e.natal, e.exact_date)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)

    deduped.sort(key=lambda e: e.exact_date)
    return deduped
