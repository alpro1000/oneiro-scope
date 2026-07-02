"""Astrocartography & relocation analysis.

Given a natal chart (date + time + place), compute:

- `relocate(natal_jd, lat, lon)` — the relocated Asc/MC/IC/Desc for any
  city on Earth. House cusps shift; planet zodiacal positions don't.
- `scan_cities(natal_jd, cities, orb)` — for a list of (name, lat, lon),
  return for each city the natal planets that fall on any angle within
  the given orb. The angles are the "doors" planets enter your life
  through in that location.

This is pure astronomy / chart geometry — symbolic interpretation is
the agent's job, not this module's. Output goes into the Strategic
Layer as `Layer.ASTRONOMY` evidence.

Reference: Jim Lewis, "Astro*Carto*Graphy" (1976).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pyswisseph is required for astrocartography"
    ) from exc

# Outer-planet calc flags use MOSEPH (analytic Moshier) so the code runs
# without binary ephemeris files. Swap to FLG_SWIEPH at deploy if .se1
# files are present at SE_EPHE_PATH.
_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED

_PLANET_NAMES = {
    swe.SUN: "Sun",
    swe.MOON: "Moon",
    swe.MERCURY: "Mercury",
    swe.VENUS: "Venus",
    swe.MARS: "Mars",
    swe.JUPITER: "Jupiter",
    swe.SATURN: "Saturn",
    swe.URANUS: "Uranus",
    swe.NEPTUNE: "Neptune",
    swe.PLUTO: "Pluto",
}

_ANGLE_NAMES = ("Asc", "MC", "IC", "Desc")


@dataclass(frozen=True)
class AngleHit:
    """One planet sitting on one of the four angles in a relocated chart."""

    planet: str
    angle: str  # "Asc" | "MC" | "IC" | "Desc"
    orb_deg: float
    planet_longitude: float
    angle_longitude: float


@dataclass(frozen=True)
class RelocationResult:
    """A relocation analysis for one city."""

    city: str
    latitude: float
    longitude: float
    asc: float
    mc: float
    ic: float
    desc: float
    angle_hits: list[AngleHit]
    # Weighted score for ranking (Venus/Jupiter on angles boost it,
    # Saturn/Pluto on angles deduct).
    score: float


def natal_planets(jd_ut: float) -> dict[str, float]:
    """Compute zodiacal longitudes of the main bodies at natal moment."""
    out: dict[str, float] = {}
    for p, name in _PLANET_NAMES.items():
        res, _ = swe.calc_ut(jd_ut, p, _FLAGS)
        out[name] = res[0]
    return out


def natal_equatorial(jd_ut: float) -> dict[str, tuple[float, float]]:
    """Compute equatorial (RA, Dec) of the main bodies at natal moment.

    Needed to draw astrocartography lines: a planet's MC/IC meridians and
    Asc/Desc horizon curves are loci in right ascension / declination, not
    ecliptic longitude.
    """
    eq_flags = swe.FLG_MOSEPH | swe.FLG_EQUATORIAL
    out: dict[str, tuple[float, float]] = {}
    for p, name in _PLANET_NAMES.items():
        res, _ = swe.calc_ut(jd_ut, p, eq_flags)
        out[name] = (res[0], res[1])  # ra, dec (degrees)
    return out


def _obliquity(jd_ut: float) -> float:
    """True obliquity of the ecliptic (degrees) at the moment."""
    return swe.calc_ut(jd_ut, swe.ECL_NUT, swe.FLG_MOSEPH)[0][0]


def chart_geometry(
    jd_ut: float,
    birth_lat: float,
    birth_lon: float,
    birth_name: str = "birth",
) -> dict:
    """Self-contained chart payload a thin client can use to compute the
    four angles for ANY clicked location on its own (no ephemeris needed
    client-side): sidereal time, obliquity, and each body's ecliptic
    longitude + equatorial RA/Dec, plus the birth coordinates.
    """
    gmst = swe.sidtime(jd_ut) * 15.0  # Greenwich sidereal time, degrees
    eps = _obliquity(jd_ut)
    ecl = natal_planets(jd_ut)
    equ = natal_equatorial(jd_ut)
    planets = {
        name: {
            "ecl_lon": round(ecl[name], 4),
            "ra": round(equ[name][0], 4),
            "dec": round(equ[name][1], 4),
        }
        for name in ecl
    }
    return {
        "gmst": round(gmst, 4),
        "obliquity": round(eps, 5),
        "planets": planets,
        "birth": {
            "lat": round(birth_lat, 4),
            "lon": round(birth_lon, 4),
            "name": birth_name,
        },
    }


def _n180(x: float) -> float:
    x = x % 360.0
    return x - 360.0 if x > 180.0 else x


def acg_lines(
    jd_ut: float,
    *,
    lat_min: float = -58.0,
    lat_max: float = 80.0,
    step: float = 1.0,
) -> dict:
    """Build the astrocartography line set as a GeoJSON FeatureCollection.

    For each planet: two MC/IC meridians (vertical, constant longitude where
    the planet culminates / anti-culminates) and two Asc/Desc horizon curves
    (longitude varies with latitude). Coordinates are [lon, lat]. Curves are
    split at the antimeridian into separate features so each is a valid
    LineString. Pure geometry — no interpretation.
    """
    import math

    gmst = swe.sidtime(jd_ut) * 15.0
    equ = natal_equatorial(jd_ut)
    features: list[dict] = []

    def _feature(planet: str, angle: str, coords: list[list[float]]) -> None:
        if len(coords) < 2:
            return
        features.append(
            {
                "type": "Feature",
                "properties": {"planet": planet, "angle": angle},
                "geometry": {"type": "LineString", "coordinates": coords},
            }
        )

    lats: list[float] = []
    phi = lat_min
    while phi <= lat_max + 1e-9:
        lats.append(round(phi, 4))
        phi += step

    for planet, (ra, dec) in equ.items():
        mc = _n180(ra - gmst)
        ic = _n180(ra - gmst + 180.0)
        _feature(planet, "MC", [[mc, lat_min], [mc, lat_max]])
        _feature(planet, "IC", [[ic, lat_min], [ic, lat_max]])

        for angle, rising in (("Asc", True), ("Desc", False)):
            seg: list[list[float]] = []
            for la in lats:
                cphi = -math.tan(math.radians(la)) * math.tan(math.radians(dec))
                if abs(cphi) > 1.0:  # circumpolar at this latitude → no rise/set
                    if len(seg) > 1:
                        _feature(planet, angle, seg)
                    seg = []
                    continue
                hour = math.degrees(math.acos(cphi))
                lon = _n180((ra - hour if rising else ra + hour) - gmst)
                if seg and abs(lon - seg[-1][0]) > 90.0:  # antimeridian wrap
                    if len(seg) > 1:
                        _feature(planet, angle, seg)
                    seg = []
                seg.append([round(lon, 3), la])
            if len(seg) > 1:
                _feature(planet, angle, seg)

    return {"type": "FeatureCollection", "features": features}


# Plain-language relocation summary -------------------------------------------
# Rule-based (symbol-dictionary tier, ~0.8 confidence). Reflective phrasing
# only — no prediction language. The four angles, the benefic/malefic split,
# and the work/home planet sets follow classical relocation practice.
_BENEFIC = {"Venus", "Jupiter"}
_CHALLENGE = {"Mars", "Saturn", "Pluto"}
_WORK_PLANETS = {"Sun", "Mercury", "Saturn", "Uranus", "Jupiter"}
_HOME_PLANETS = {"Venus", "Moon", "Jupiter"}

_PLANET_RU = {
    "Sun": "Солнце", "Moon": "Луна", "Mercury": "Меркурий", "Venus": "Венера",
    "Mars": "Марс", "Jupiter": "Юпитер", "Saturn": "Сатурн", "Uranus": "Уран",
    "Neptune": "Нептун", "Pluto": "Плутон",
}


def relocation_summary(result: "RelocationResult", locale: str = "ru") -> dict:
    """Turn a RelocationResult into a plain-language work/life summary.

    Deterministic and reflective: classifies the tight angle contacts into
    career-supportive, home-comforting, relationship, and tension buckets,
    then composes a one-line verdict. Returns both structured tags and text
    so a UI can render either.
    """
    work: list[str] = []
    home: list[str] = []
    rel: list[str] = []
    warn: list[str] = []
    ru = locale == "ru"

    def name(p: str) -> str:
        return _PLANET_RU[p] if ru else p

    def add(bucket: list[str], item: str) -> None:
        if item not in bucket:
            bucket.append(item)

    for h in result.angle_hits:
        if h.orb_deg > 6.0:
            continue
        p, a = h.planet, h.angle
        if a in ("MC", "Asc") and p in _WORK_PLANETS:
            add(work, name(p))
        if a in ("IC", "Asc") and p in _HOME_PLANETS:
            add(home, name(p))
        if a == "Desc" and (p in _BENEFIC or p in ("Sun", "Mercury")):
            add(rel, name(p))
        if a in ("IC", "Asc") and p in _CHALLENGE:
            add(warn, name(p))

    good_work = bool(work)
    soft_home = bool(home)
    hard_home = bool(warn)

    if ru:
        if good_work and hard_home:
            plain = ("Сюда — работать и расти, но дом может быть беспокойным: "
                     "хорошо для карьерного рывка, хуже для тихой жизни.")
        elif good_work and soft_home:
            plain = ("Редкое сочетание: поддержаны и карьера, и уют — "
                     "сбалансированное место.")
        elif good_work:
            plain = "Место скорее про дело и реализацию; жильё нейтрально."
        elif soft_home and not hard_home:
            plain = "Место скорее про дом, уют и отдых; карьерно спокойно."
        elif hard_home:
            plain = ("Жить тут энергозатратно (напряжение в быту) — "
                     "подходит для коротких интенсивных периодов.")
        else:
            plain = "Нейтральная зона: ярких угловых линий рядом нет."
    else:
        if good_work and hard_home:
            plain = ("Strong for work and growth, but home life can feel "
                     "restless — great for a career push, less for quiet living.")
        elif good_work and soft_home:
            plain = "Rare blend: both career and comfort are supported — balanced."
        elif good_work:
            plain = "More about work and achievement; living is neutral."
        elif soft_home and not hard_home:
            plain = "More about home, comfort and rest; career stays calm."
        elif hard_home:
            plain = ("Living here is demanding (domestic tension) — better for "
                     "short, intense periods.")
        else:
            plain = "Neutral zone: no strong angular lines nearby."

    # "Clean" luck: a benefic sits on an angle with no malefic angular
    # contact nearby. Session testing showed this flag changes the read
    # entirely (Venus-IC Prague looks lucky until you see Mars-IC 0.3°).
    benefic_hits = [
        h for h in result.angle_hits
        if h.planet in _BENEFIC and h.orb_deg <= 6.0
    ]
    malefic_hits = [
        h for h in result.angle_hits
        if h.planet in _CHALLENGE and h.orb_deg <= 6.0
    ]
    clean = bool(benefic_hits) and not malefic_hits

    return {
        "plain": plain,
        "work": work,
        "home": home,
        "relationships": rel,
        "tension": warn,
        "clean": clean,
        "luck": [name(h.planet) for h in benefic_hits],
        "confidence": 0.8,
        "source": "relocation rule-set (classical angle practice)",
    }


# Multi-location comparison + thematic scan --------------------------------

# theme -> predicate over (planet, angle). Mirrors the four questions
# users actually asked in session testing.
_THEME_RULES = {
    "luck": lambda p, a: p in ("Jupiter", "Venus"),
    "career": lambda p, a: a == "MC" and p in (
        "Sun", "Jupiter", "Uranus", "Mercury", "Saturn"
    ),
    "relationships": lambda p, a: a == "Desc" and p in (
        "Venus", "Jupiter", "Sun", "Moon", "Mercury"
    ),
    "home": lambda p, a: a in ("IC", "Asc") and p in (
        "Venus", "Moon", "Jupiter"
    ),
}


def compare_locations(
    jd_ut: float,
    locations: list[tuple[str, float, float]],
    *,
    orb_deg: float = 8.0,
    locale: str = "ru",
) -> list[dict]:
    """Side-by-side relocation read for a handful of places — the
    'Zaporizhzhia vs Samara vs London' view. Returns one dict per
    location, input order preserved (comparison, not ranking)."""
    planets = natal_planets(jd_ut)
    out = []
    for name, lat, lon in locations:
        r = relocate(jd_ut, lat, lon, planets=planets, orb_deg=orb_deg)
        out.append(
            {
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "angles": {"asc": r.asc, "mc": r.mc, "ic": r.ic, "desc": r.desc},
                "angle_hits": [
                    {
                        "planet": h.planet,
                        "angle": h.angle,
                        "orb_deg": h.orb_deg,
                    }
                    for h in sorted(r.angle_hits, key=lambda h: h.orb_deg)
                ],
                "score": r.score,
                "summary": relocation_summary(r, locale=locale),
            }
        )
    return out


def theme_scan(
    jd_ut: float,
    cities: list[tuple[str, float, float]],
    theme: str,
    *,
    orb_deg: float = 6.0,
    top_n: int = 10,
) -> list[dict]:
    """Rank cities for one theme (luck/career/relationships/home).

    A city qualifies when a theme-matching planet sits on an angle
    within `orb_deg`; entries carry the matching hits, the full hit
    list, and the clean flag so callers can render '✅ чисто' vs
    '⚠️ с минусом' honestly.
    """
    if theme not in _THEME_RULES:
        raise ValueError(
            f"Unknown theme {theme!r}; expected one of {sorted(_THEME_RULES)}"
        )
    rule = _THEME_RULES[theme]
    planets = natal_planets(jd_ut)
    rows = []
    for name, lat, lon in cities:
        r = relocate(jd_ut, lat, lon, planets=planets, orb_deg=orb_deg)
        matches = [
            h for h in r.angle_hits
            if rule(h.planet, h.angle) and h.orb_deg <= orb_deg
        ]
        if not matches:
            continue
        malefics = [
            h for h in r.angle_hits
            if h.planet in _CHALLENGE and h.orb_deg <= orb_deg
        ]
        rows.append(
            {
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "best_orb": min(h.orb_deg for h in matches),
                "matches": [
                    {"planet": h.planet, "angle": h.angle, "orb_deg": h.orb_deg}
                    for h in sorted(matches, key=lambda h: h.orb_deg)
                ],
                "malefics": [
                    {"planet": h.planet, "angle": h.angle, "orb_deg": h.orb_deg}
                    for h in sorted(malefics, key=lambda h: h.orb_deg)
                ],
                "clean": not malefics,
                "score": r.score,
            }
        )
    rows.sort(key=lambda x: (-x["score"], x["best_orb"]))
    return rows[:top_n]


def _angle_diff_deg(a: float, b: float) -> float:
    """Smallest angular distance between two longitudes (0-180°)."""
    d = abs(a - b) % 360
    if d > 180:
        d = 360 - d
    return d


def relocate(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    planets: Optional[dict[str, float]] = None,
    orb_deg: float = 7.0,
) -> RelocationResult:
    """Compute the relocated Asc/MC/IC/Desc for `(lat, lon)` at the given
    natal moment and list which natal planets fall on any angle within
    `orb_deg`.
    """
    if planets is None:
        planets = natal_planets(jd_ut)

    cusps, ascmc = swe.houses(jd_ut, latitude, longitude, b"P")
    asc = ascmc[0]
    mc = ascmc[1]
    ic = (mc + 180.0) % 360.0
    desc = (asc + 180.0) % 360.0

    angles = {"Asc": asc, "MC": mc, "IC": ic, "Desc": desc}

    hits: list[AngleHit] = []
    for angle_name, angle_lon in angles.items():
        for planet_name, plon in planets.items():
            orb = _angle_diff_deg(plon, angle_lon)
            if orb <= orb_deg:
                hits.append(
                    AngleHit(
                        planet=planet_name,
                        angle=angle_name,
                        orb_deg=round(orb, 2),
                        planet_longitude=round(plon, 4),
                        angle_longitude=round(angle_lon, 4),
                    )
                )

    score = _score_hits(hits)
    return RelocationResult(
        city=f"({latitude:.4f},{longitude:.4f})",
        latitude=latitude,
        longitude=longitude,
        asc=round(asc, 4),
        mc=round(mc, 4),
        ic=round(ic, 4),
        desc=round(desc, 4),
        angle_hits=hits,
        score=score,
    )


# Weights for the heuristic score. Astrology tradition treats Venus/Jupiter
# as benefics, Saturn/Pluto/Mars as challenging on angles. Sun/Moon are
# strong but neutral.
_BENEFICS = {"Venus": 3.0, "Jupiter": 3.0, "Sun": 1.0, "Moon": 1.0}
_MALEFICS = {"Saturn": -1.5, "Pluto": -1.5, "Mars": -1.0}
_ANGLE_WEIGHT = {"Asc": 2.0, "MC": 2.0, "IC": 1.5, "Desc": 1.0}


def _score_hits(hits: list[AngleHit]) -> float:
    """Heuristic: sum of (planet weight) * (angle weight) * orb falloff."""
    total = 0.0
    for h in hits:
        pw = _BENEFICS.get(h.planet, 0) + _MALEFICS.get(h.planet, 0)
        aw = _ANGLE_WEIGHT[h.angle]
        # Linear falloff to zero at orb_deg=7.
        falloff = max(0.0, 1.0 - h.orb_deg / 7.0)
        total += pw * aw * falloff
    return round(total, 2)


def scan_cities(
    jd_ut: float,
    cities: list[tuple[str, float, float]],
    *,
    orb_deg: float = 7.0,
) -> list[RelocationResult]:
    """Run `relocate` for each `(name, lat, lon)` city, sorted by score
    descending. Planets are computed once."""
    planets = natal_planets(jd_ut)
    results = []
    for name, lat, lon in cities:
        r = relocate(jd_ut, lat, lon, planets=planets, orb_deg=orb_deg)
        results.append(
            RelocationResult(
                city=name,
                latitude=lat,
                longitude=lon,
                asc=r.asc,
                mc=r.mc,
                ic=r.ic,
                desc=r.desc,
                angle_hits=r.angle_hits,
                score=r.score,
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results
