"""Thematic transit arcs — a phase timeline for one life theme.

Instead of a flat list of transit dates, groups slow-planet transits to
a theme's natal significators (money/debt, career, relationships, home)
into chronological phases: pressure runs, turning points, support runs.
This is the "crisis → turning point → closure" storyline that users ask
for ("расшпиши строго по транзитам ситуацию с долгом").

Significators are derived deterministically from the natal chart:
planets occupying the theme's houses + the rulers of the theme's cusps
+ the theme's natural planets. Geometry is ASTRONOMY; phase labels are
a fixed rule (symbol tier) — descriptive of pressure/support, never a
verdict on outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover
    raise ImportError("pyswisseph is required for transit arcs") from exc

from backend.services.astrology.transits_engine import TransitEvent, find_transits

from backend.core.ephemeris import FLAGS as _FLAGS

_BODIES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
}

# Sign rulers (classical, as used across the knowledge base).
_SIGN_RULERS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Pluto", "Jupiter", "Saturn", "Uranus", "Neptune",
]

# theme -> (houses, natural significators)
_THEMES = {
    "money_debt": ((2, 8), {"Venus", "Jupiter"}),
    "career": ((10, 6), {"Sun", "Saturn"}),
    "relationships": ((7, 5), {"Venus", "Moon"}),
    "home": ((4,), {"Moon", "Venus"}),
}

_HARMONIOUS = {"trine", "sextile", "conjunction"}


@dataclass(frozen=True)
class ArcPhase:
    start: str  # YYYY-MM
    end: str
    kind: str  # "pressure" | "support" | "mixed"
    events: tuple


@dataclass
class ThematicArc:
    theme: str
    significators: list[str] = field(default_factory=list)
    events: list[TransitEvent] = field(default_factory=list)
    phases: list[ArcPhase] = field(default_factory=list)
    turning_point: str | None = None  # first month support becomes dominant


def _houses(jd_ut: float, lat: float, lon: float) -> list[float]:
    cusps, _ = swe.houses(jd_ut, lat, lon, b"P")
    return list(cusps)[:12]


def _house_of(lon_deg: float, cusps: list[float]) -> int:
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if a < b:
            if a <= lon_deg < b:
                return i + 1
        elif lon_deg >= a or lon_deg < b:
            return i + 1
    return 1


def theme_significators(
    jd_ut: float, birth_lat: float, birth_lon: float, theme: str
) -> list[str]:
    """Natal significators for a theme: occupants of the theme houses +
    rulers of their cusps + the theme's natural planets. Restricted to
    the bodies the transit engine tracks natally."""
    if theme not in _THEMES:
        raise ValueError(
            f"Unknown theme {theme!r}; expected one of {sorted(_THEMES)}"
        )
    houses, natural = _THEMES[theme]
    cusps = _houses(jd_ut, birth_lat, birth_lon)

    sig: set[str] = set(natural)
    for name, code in _BODIES.items():
        lon = swe.calc_ut(jd_ut, code, _FLAGS)[0][0]
        if _house_of(lon, cusps) in houses:
            sig.add(name)
    for h in houses:
        sig.add(_SIGN_RULERS[int(cusps[h - 1] // 30) % 12])

    trackable = {n for _, n in [
        (swe.SUN, "Sun"), (swe.MOON, "Moon"), (swe.MERCURY, "Mercury"),
        (swe.VENUS, "Venus"), (swe.MARS, "Mars"), (swe.JUPITER, "Jupiter"),
        (swe.SATURN, "Saturn"),
    ]}
    return sorted(sig & trackable)


def compute_arc(
    jd_ut: float,
    birth_lat: float,
    birth_lon: float,
    theme: str,
    start: date,
    end: date,
    *,
    orb_deg: float = 1.2,
) -> ThematicArc:
    """Filter slow transits to a theme's significators and phase them."""
    sig = theme_significators(jd_ut, birth_lat, birth_lon, theme)
    slow = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    events = [
        e for e in find_transits(jd_ut, start, end, orb_deg=orb_deg)
        if e.natal in sig and e.transiting in slow
    ]
    events.sort(key=lambda e: e.exact_date)

    arc = ThematicArc(theme=theme, significators=sig, events=events)
    arc.phases = _phase(events)
    arc.turning_point = _turning_point(arc.phases)
    return arc


def _month(e: TransitEvent) -> str:
    return e.exact_date[:7]


def _phase(events: list[TransitEvent]) -> list[ArcPhase]:
    """Group consecutive events into runs by dominant polarity."""
    if not events:
        return []
    phases: list[ArcPhase] = []
    run: list[TransitEvent] = [events[0]]

    def polarity(e: TransitEvent) -> str:
        return "support" if e.aspect in _HARMONIOUS else "pressure"

    cur = polarity(events[0])
    for e in events[1:]:
        p = polarity(e)
        if p == cur:
            run.append(e)
        else:
            phases.append(
                ArcPhase(_month(run[0]), _month(run[-1]), cur, tuple(run))
            )
            run = [e]
            cur = p
    phases.append(ArcPhase(_month(run[0]), _month(run[-1]), cur, tuple(run)))
    return phases


def _turning_point(phases: list[ArcPhase]) -> str | None:
    """First month where a support phase follows pressure and support
    stays dominant for the rest of the arc (>=60% of later events)."""
    for i, ph in enumerate(phases):
        if ph.kind != "support" or i == 0:
            continue
        later = phases[i:]
        support_n = sum(len(p.events) for p in later if p.kind == "support")
        total_n = sum(len(p.events) for p in later)
        if total_n and support_n / total_n >= 0.6:
            return ph.start
    return None
