"""Deterministic compute core for the analysis-patterns catalog.

Implements the ASTRONOMY-layer (confidence 1.0) computations behind
`knowledge_base/analysis_patterns.json`: natal geometry with house
rulers / dignities / Part of Fortune, money-contour structure, vocation
signals, decade transit maps, life-pivot scans, and hour-by-hour
electional data. Plus the reverse-physiognomy KB lookup (dictionary
tier, 0.6).

Everything here is sky math or KB lookup — NO interpretation and NO
LLM. Symbolic reading happens in the skills layer, guided by the
`interprets.rules` of each pattern in the catalog.

Engine: Swiss Ephemeris in Moshier mode (no data files needed),
mirroring `backend/services/lunar/engine.py` fallback behaviour.
"""

from __future__ import annotations

import json
from datetime import date as date_cls, datetime, time as time_cls, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

try:
    import swisseph as swe
except ImportError as exc:  # pragma: no cover
    raise ImportError("pyswisseph required for pattern_engine") from exc

_FLG = swe.FLG_MOSEPH | swe.FLG_SPEED

SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]

# Traditional rulers first, modern co-rulers second (both surfaced;
# the skill cites which convention it reads).
SIGN_RULERS: dict[str, list[str]] = {
    "aries": ["mars"], "taurus": ["venus"], "gemini": ["mercury"],
    "cancer": ["moon"], "leo": ["sun"], "virgo": ["mercury"],
    "libra": ["venus"], "scorpio": ["mars", "pluto"],
    "sagittarius": ["jupiter"], "capricorn": ["saturn"],
    "aquarius": ["saturn", "uranus"], "pisces": ["jupiter", "neptune"],
}

PLANET_IDS: dict[str, int] = {
    "sun": swe.SUN, "moon": swe.MOON, "mercury": swe.MERCURY,
    "venus": swe.VENUS, "mars": swe.MARS, "jupiter": swe.JUPITER,
    "saturn": swe.SATURN, "uranus": swe.URANUS, "neptune": swe.NEPTUNE,
    "pluto": swe.PLUTO, "mean_node": swe.MEAN_NODE,
}
_CLASSICAL7 = ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn")
_SLOW = ("jupiter", "saturn", "uranus", "neptune", "pluto")

ASPECTS: dict[int, str] = {
    0: "conjunction", 60: "sextile", 90: "square", 120: "trine", 180: "opposition",
}
ASPECT_NATURE: dict[str, str] = {
    "conjunction": "neutral", "sextile": "harmonious", "trine": "harmonious",
    "square": "tense", "opposition": "tense",
}

_PROVENANCE = {
    "ephemeris_engine": "SwissEph/MOSEPH",
    "house_system": "Placidus",
    "zodiac": "tropical",
}


# --- primitives ---------------------------------------------------------------

def _to_utc(birth_date: str, birth_time: str, tz_name: str) -> datetime:
    d = date_cls.fromisoformat(birth_date)
    t = time_cls.fromisoformat(birth_time)
    local = datetime(d.year, d.month, d.day, t.hour, t.minute, t.second,
                     tzinfo=ZoneInfo(tz_name))
    return local.astimezone(timezone.utc)


def _jd(dt_utc: datetime) -> float:
    return swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )


def _lon(jd_ut: float, planet: str) -> tuple[float, float]:
    """(ecliptic longitude, speed) of a planet at JD UT."""
    xx, _ = swe.calc_ut(jd_ut, PLANET_IDS[planet], _FLG)
    return xx[0] % 360.0, xx[3]


def _sign(lon: float) -> str:
    return SIGNS[int((lon % 360.0) // 30)]


def _sep(a: float, b: float) -> float:
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def _aspect_hit(a: float, b: float, orb: float) -> Optional[tuple[str, float]]:
    sep = _sep(a, b)
    for angle, name in ASPECTS.items():
        off = abs(sep - angle)
        if off <= orb:
            return name, round(off, 2)
    return None


def _house_of(lon: float, cusps: tuple[float, ...]) -> int:
    lon %= 360.0
    for i in range(12):
        a, b = cusps[i] % 360.0, cusps[(i + 1) % 12] % 360.0
        if (a < b and a <= lon < b) or (a >= b and (lon >= a or lon < b)):
            return i + 1
    return 12  # numeric edge fallback


# Classical essential dignities (Ptolemy, Tetrabiblos I.17-19). Kept
# inline so the engine stays importable without the astrology-service
# stack (geocoder etc.) — same rationale as lunar/engine.py. Detriment
# and fall are the signs opposite domicile and exaltation.
_DOMICILE: dict[str, tuple[str, ...]] = {
    "sun": ("leo",), "moon": ("cancer",), "mercury": ("gemini", "virgo"),
    "venus": ("taurus", "libra"), "mars": ("aries", "scorpio"),
    "jupiter": ("sagittarius", "pisces"), "saturn": ("capricorn", "aquarius"),
}
_EXALTATION: dict[str, str] = {
    "sun": "aries", "moon": "taurus", "mercury": "virgo", "venus": "pisces",
    "mars": "capricorn", "jupiter": "cancer", "saturn": "libra",
}


def _opposite(sign: str) -> str:
    return SIGNS[(SIGNS.index(sign) + 6) % 12]


def _dignity(planet: str, sign: str) -> Optional[str]:
    if planet not in _CLASSICAL7:
        return None  # modern planets: no classical dignity
    if sign in _DOMICILE[planet]:
        return "domicile"
    if sign == _EXALTATION[planet]:
        return "exaltation"
    if sign in tuple(_opposite(s) for s in _DOMICILE[planet]):
        return "detriment"
    if sign == _opposite(_EXALTATION[planet]):
        return "fall"
    return "peregrine"


# --- natal geometry -----------------------------------------------------------

def natal_geometry(
    birth_date: str, birth_time: str, birth_timezone: str,
    lat: float, lon: float,
) -> dict[str, Any]:
    """Full natal geometry: planets/houses/angles/sect/Part of Fortune.

    Pure astronomy (confidence 1.0). The dict is the shared input of the
    pattern computations below.
    """
    utc = _to_utc(birth_date, birth_time, birth_timezone)
    jd_ut = _jd(utc)
    cusps, ascmc = swe.houses(jd_ut, lat, lon, b"P")
    asc, mc = ascmc[0] % 360.0, ascmc[1] % 360.0
    angles = {
        "asc": asc, "mc": mc,
        "ic": (mc + 180.0) % 360.0, "dsc": (asc + 180.0) % 360.0,
    }

    planets: dict[str, dict[str, Any]] = {}
    for name in PLANET_IDS:
        plon, speed = _lon(jd_ut, name)
        sign = _sign(plon)
        planets[name] = {
            "lon": round(plon, 2),
            "sign": sign,
            "deg_in_sign": round(plon % 30.0, 2),
            "retrograde": speed < 0,
            "house": _house_of(plon, cusps),
            "dignity": _dignity(name, sign),
        }

    sun_house = planets["sun"]["house"]
    sect = "night" if sun_house in (1, 2, 3, 4, 5, 6) else "day"
    s, m = planets["sun"]["lon"], planets["moon"]["lon"]
    pof_lon = (asc + m - s) % 360.0 if sect == "day" else (asc + s - m) % 360.0
    pof_sign = _sign(pof_lon)
    pof_ruler = SIGN_RULERS[pof_sign][0]
    part_of_fortune = {
        "lon": round(pof_lon, 2),
        "sign": pof_sign,
        "house": _house_of(pof_lon, cusps),
        "dispositor": {"planet": pof_ruler, **_placement(planets, pof_ruler)},
    }

    return {
        "jd_ut": round(jd_ut, 5),
        "utc": utc.isoformat(),
        "planets": planets,
        "cusps": {i + 1: round(c % 360.0, 2) for i, c in enumerate(cusps[:12])},
        "cusp_signs": {i + 1: _sign(c) for i, c in enumerate(cusps[:12])},
        "angles": {k: round(v, 2) for k, v in angles.items()},
        "sect": sect,
        "part_of_fortune": part_of_fortune,
        "provenance": dict(_PROVENANCE),
    }


def _placement(planets: dict[str, dict], name: str) -> dict[str, Any]:
    p = planets[name]
    return {"sign": p["sign"], "house": p["house"], "dignity": p["dignity"],
            "retrograde": p["retrograde"]}


def _house_block(geo: dict, n: int) -> dict[str, Any]:
    """Cusp sign + rulers (with placements) + occupants of house `n`."""
    sign = geo["cusp_signs"][n]
    rulers = [
        {"planet": r, **_placement(geo["planets"], r)}
        for r in SIGN_RULERS[sign]
    ]
    occupants = [
        {"planet": name, **_placement(geo["planets"], name)}
        for name, p in geo["planets"].items() if p["house"] == n
    ]
    return {"house": n, "cusp_sign": sign, "rulers": rulers, "occupants": occupants}


# --- pattern: money-contour ---------------------------------------------------

def money_contour(geo: dict[str, Any]) -> dict[str, Any]:
    """Structural money facts: 2nd/8th/11th houses, linchpin, Fortune."""
    h2, h8, h11 = _house_block(geo, 2), _house_block(geo, 8), _house_block(geo, 11)

    linchpin: dict[str, Any] = {"linked": False}
    best: Optional[tuple[float, str, str]] = None
    for r2 in (r["planet"] for r in h2["rulers"]):
        for r8 in (r["planet"] for r in h8["rulers"]):
            if r2 == r8:
                linchpin = {"linked": True, "type": "same_ruler", "planet": r2}
                best = None
                break
            sep = _sep(geo["planets"][r2]["lon"], geo["planets"][r8]["lon"])
            if best is None or sep < best[0]:
                best = (sep, r2, r8)
        if linchpin["linked"]:
            break
    if best is not None:
        sep, r2, r8 = best
        linchpin = {
            "linked": sep <= 8.0, "type": "conjunction_of_rulers",
            "ruler_2nd": r2, "ruler_8th": r8,
            "separation_deg": round(sep, 1),
            "same_sign": geo["planets"][r2]["sign"] == geo["planets"][r8]["sign"],
            "same_house": geo["planets"][r2]["house"] == geo["planets"][r8]["house"],
        }

    return {
        "house_2": h2, "house_8": h8, "house_11": h11,
        "linchpin": linchpin,
        "part_of_fortune": geo["part_of_fortune"],
        "sect": geo["sect"],
        "rulership_source": "traditional rulerships incl. modern co-rulers",
    }


# --- pattern: vocation-map ----------------------------------------------------

def vocation_map(geo: dict[str, Any], conj_orb: float = 8.0) -> dict[str, Any]:
    """Vocation signals: MC complex, work houses, dignities, angularity."""
    mc_lon = geo["angles"]["mc"]
    mc_sign = _sign(mc_lon)
    planets = geo["planets"]
    return {
        "mc": {
            "sign": mc_sign,
            "rulers": [
                {"planet": r, **_placement(planets, r)}
                for r in SIGN_RULERS[mc_sign]
            ],
            "conjunct": [
                {"planet": n, "orb_deg": round(_sep(p["lon"], mc_lon), 1)}
                for n, p in planets.items()
                if n != "mean_node" and _sep(p["lon"], mc_lon) <= conj_orb
            ],
        },
        "work_houses": {
            "2": _house_block(geo, 2),
            "6": _house_block(geo, 6),
            "10": _house_block(geo, 10),
        },
        "dignified": [
            {"planet": n, "sign": p["sign"], "status": p["dignity"], "house": p["house"]}
            for n, p in planets.items()
            if p["dignity"] in ("domicile", "exaltation")
        ],
        "angular": [
            {"planet": n, "house": p["house"], "sign": p["sign"]}
            for n, p in planets.items()
            if n != "mean_node" and p["house"] in (1, 4, 7, 10)
        ],
        "part_of_fortune": geo["part_of_fortune"],
    }


# --- pattern: decade-map ------------------------------------------------------

def _natal_points(geo: dict) -> dict[str, float]:
    pts = {n: p["lon"] for n, p in geo["planets"].items() if n != "mean_node"}
    pts.update(geo["angles"])
    return pts


def decade_map(
    geo: dict[str, Any], start_year: int, years: int = 10,
) -> dict[str, Any]:
    """Year-by-year slow-planet map + dated aspect hits to natal points."""
    years = max(1, min(int(years), 12))
    natal_pts = _natal_points(geo)

    # monthly hit scan with dedupe per (planet, aspect, point)
    last_seen: dict[tuple[str, str, str], date_cls] = {}
    hits_by_year: dict[int, list[dict]] = {y: [] for y in range(start_year, start_year + years)}
    d = date_cls(start_year, 1, 1)
    end = date_cls(start_year + years, 1, 1)
    while d < end:
        jd_ut = swe.julday(d.year, d.month, d.day, 12.0)
        for tp in _SLOW:
            tlon, _ = _lon(jd_ut, tp)
            for pn, plon in natal_pts.items():
                hit = _aspect_hit(tlon, plon, orb=1.5)
                if hit is None:
                    continue
                aspect, orb = hit
                key = (tp, aspect, pn)
                prev = last_seen.get(key)
                if prev is None or (d - prev).days > 300:
                    flags = []
                    if tp == "saturn" and pn == "saturn" and aspect == "conjunction":
                        flags.append("saturn_return")
                    if tp == "jupiter" and pn == "jupiter" and aspect == "conjunction":
                        flags.append("jupiter_return")
                    if pn in ("asc", "mc", "ic", "dsc") and aspect == "conjunction":
                        flags.append("angle_crossing")
                    hits_by_year[d.year].append({
                        "date": f"{d.year}-{d.month:02d}",
                        "transiting": tp, "aspect": aspect, "natal": pn,
                        "orb_deg": orb, "flags": flags,
                    })
                last_seen[key] = d
        d = (d.replace(day=1) + timedelta(days=32)).replace(day=1)

    out_years = []
    for y in range(start_year, start_year + years):
        jd_mid = swe.julday(y, 7, 1, 12.0)
        placements = {}
        for tp in _SLOW:
            tlon, _ = _lon(jd_mid, tp)
            placements[tp] = {
                "sign": _sign(tlon),
                "deg_in_sign": round(tlon % 30.0, 1),
                "natal_house": _house_of(
                    tlon, tuple(geo["cusps"][i] for i in range(1, 13))
                ),
            }
        out_years.append({"year": y, "placements_jul1": placements,
                          "hits": hits_by_year[y]})
    return {"start_year": start_year, "years": out_years}


# --- pattern: life-pivots -----------------------------------------------------

_PIVOT_PLANETS = ("saturn", "uranus", "neptune", "pluto")
_PIVOT_POINTS = ("asc", "mc", "ic", "dsc", "sun", "moon")


def life_pivots(
    geo: dict[str, Any], from_year: int, to_year: int,
) -> dict[str, Any]:
    """Dated slow-planet conjunctions to angles/luminaries + cycle windows."""
    if to_year <= from_year:
        raise ValueError("to_year must be after from_year")
    if to_year - from_year > 60:
        raise ValueError("scan window capped at 60 years")

    pts = {**{k: geo["angles"][k] for k in ("asc", "mc", "ic", "dsc")},
           "sun": geo["planets"]["sun"]["lon"],
           "moon": geo["planets"]["moon"]["lon"]}
    natal_saturn = geo["planets"]["saturn"]["lon"]
    natal_uranus = geo["planets"]["uranus"]["lon"]
    birth_year = int(geo["utc"][:4])

    windows: list[dict] = []
    cycles: list[dict] = []
    last: dict[tuple[str, str], date_cls] = {}

    d = date_cls(from_year, 1, 1)
    end = date_cls(to_year + 1, 1, 1)
    while d < end:
        jd_ut = swe.julday(d.year, d.month, d.day, 12.0)
        for tp in _PIVOT_PLANETS:
            tlon, _ = _lon(jd_ut, tp)
            for pn, plon in pts.items():
                if _sep(tlon, plon) <= 1.0:
                    key = (tp, pn)
                    prev = last.get(key)
                    if prev is None or (d - prev).days > 420:
                        relocation = ("strong" if pn == "ic"
                                      else "possible" if pn in ("asc", "moon")
                                      else None)
                        windows.append({
                            "date": f"{d.year}-{d.month:02d}",
                            "age": d.year - birth_year,
                            "transiting": tp, "point": pn,
                            "orb_deg": round(_sep(tlon, plon), 1),
                            "relocation_marker": relocation,
                        })
                    last[key] = d
            # cycle detection
            if tp == "saturn" and _sep(tlon, natal_saturn) <= 1.0:
                key = ("saturn", "return")
                prev = last.get(key)
                if prev is None or (d - prev).days > 420:
                    cycles.append({"cycle": "saturn_return",
                                   "date": f"{d.year}-{d.month:02d}",
                                   "age": d.year - birth_year})
                last[key] = d
            if tp == "uranus" and _sep(tlon, (natal_uranus + 180.0) % 360.0) <= 1.0:
                key = ("uranus", "opposition")
                prev = last.get(key)
                if prev is None or (d - prev).days > 420:
                    cycles.append({"cycle": "uranus_opposition",
                                   "date": f"{d.year}-{d.month:02d}",
                                   "age": d.year - birth_year})
                last[key] = d
        d = (d.replace(day=1) + timedelta(days=32)).replace(day=1)

    windows.sort(key=lambda w: w["date"])
    questions = [
        (f"{w['date']} (возраст ~{w['age']}): что происходило вокруг этой даты? "
         + ("Была ли смена жилья/переезд?" if w["relocation_marker"]
            else "Была ли смена этапа (работа, статус, среда)?"))
        for w in windows
    ]
    return {"windows": windows, "cycles": cycles,
            "validation_questions": questions,
            "scan": {"from_year": from_year, "to_year": to_year,
                     "orb_deg": 1.0, "step": "monthly"}}


# --- pattern: electional-day --------------------------------------------------

_ELECTIONAL_NATAL = ("sun", "moon", "mercury", "venus", "mars")


def electional_day(
    geo: dict[str, Any], target_date: str, tz_name: str,
    day_start: int = 6, day_end: int = 22, step_min: int = 30,
) -> dict[str, Any]:
    """Hour-by-hour Moon data for one day: aspects, VoC, phase, Mercury."""
    tz = ZoneInfo(tz_name)
    d = date_cls.fromisoformat(target_date)
    natal_pts = {n: geo["planets"][n]["lon"] for n in _ELECTIONAL_NATAL}
    natal_pts["asc"] = geo["angles"]["asc"]
    natal_pts["mc"] = geo["angles"]["mc"]

    def moon_at(dt_local: datetime) -> float:
        return _lon(_jd(dt_local.astimezone(timezone.utc)), "moon")[0]

    start_local = datetime(d.year, d.month, d.day, day_start, 0, tzinfo=tz)
    start_sign = _sign(moon_at(start_local))

    # ingress: first sign change on a 10-min grid within 80h
    ingress_local: Optional[datetime] = None
    t = start_local
    for _ in range(6 * 80):
        t = t + timedelta(minutes=10)
        if _sign(moon_at(t)) != start_sign:
            ingress_local = t
            break

    # exact aspects (Moon -> classical planets except Moon) on the same grid,
    # from 72h before ingress up to ingress: sign-change of the offset.
    voc_start: Optional[datetime] = None
    if ingress_local is not None:
        others = [p for p in _CLASSICAL7 if p != "moon"]
        grid0 = ingress_local - timedelta(hours=72)
        prev_off: dict[tuple[str, int], float] = {}
        last_exact: Optional[datetime] = None
        t = grid0
        while t <= ingress_local:
            jd_ut = _jd(t.astimezone(timezone.utc))
            mlon = _lon(jd_ut, "moon")[0]
            for p in others:
                plon = _lon(jd_ut, p)[0]
                for angle in ASPECTS:
                    diff = ((mlon - plon - angle) + 180.0) % 360.0 - 180.0
                    key = (p, angle)
                    if key in prev_off and prev_off[key] * diff < 0 \
                            and abs(diff) < 5.0:
                        last_exact = t
                    prev_off[key] = diff
            t += timedelta(minutes=10)
        voc_start = last_exact

    steps = []
    t = start_local
    end_local = datetime(d.year, d.month, d.day, day_end, 0, tzinfo=tz)
    while t <= end_local:
        jd_ut = _jd(t.astimezone(timezone.utc))
        mlon = _lon(jd_ut, "moon")[0]
        hits = []
        for pn, plon in natal_pts.items():
            hit = _aspect_hit(mlon, plon, orb=1.0)
            if hit:
                aspect, orb = hit
                hits.append({"natal": pn, "aspect": aspect, "orb_deg": orb,
                             "nature": ASPECT_NATURE[aspect]})
        in_voc = bool(
            voc_start is not None and ingress_local is not None
            and voc_start <= t < ingress_local
        )
        steps.append({
            "time": t.strftime("%H:%M"),
            "moon_lon": round(mlon, 1),
            "moon_sign": _sign(mlon),
            "natal_hits": hits,
            "void_of_course": in_voc,
        })
        t += timedelta(minutes=step_min)

    noon = datetime(d.year, d.month, d.day, 12, 0, tzinfo=tz)
    jd_noon = _jd(noon.astimezone(timezone.utc))
    sun_lon = _lon(jd_noon, "sun")[0]
    moon_lon = _lon(jd_noon, "moon")[0]
    elong = (moon_lon - sun_lon) % 360.0
    merc_speed = _lon(jd_noon, "mercury")[1]

    supportive = [
        s["time"] for s in steps
        if not s["void_of_course"]
        and any(h["nature"] == "harmonious" for h in s["natal_hits"])
    ]
    return {
        "date": target_date,
        "timezone": tz_name,
        "moon_sign_at_start": start_sign,
        "phase": {
            "elongation_deg": round(elong, 1),
            "waxing": elong < 180.0,
        },
        "mercury_retrograde": merc_speed < 0,
        "ingress_local": ingress_local.strftime("%Y-%m-%d %H:%M") if ingress_local else None,
        "void_of_course": {
            "start_local": voc_start.strftime("%Y-%m-%d %H:%M") if voc_start else None,
            "end_local": ingress_local.strftime("%Y-%m-%d %H:%M") if ingress_local else None,
        },
        "steps": steps,
        "supportive_step_times": supportive,
        "methodology": (
            "Moon per step; natal-aspect orb 1.0°; VoC = after last exact "
            "Ptolemaic aspect to Sun..Saturn before sign ingress (10-min grid)"
        ),
    }


# --- pattern: reverse-physiognomy ---------------------------------------------

_KB_DIR = Path(__file__).resolve().parent.parent / "physiognomy" / "knowledge_base"

# Deterministic trait-keyword → KB entry index. Keys are lowercase
# substrings matched against the user-supplied trait strings (ru/en).
_TRAIT_INDEX: list[tuple[tuple[str, ...], str, tuple[str, ...]]] = [
    # (keywords, kb_file, path in json)
    (("дисциплин", "порядок", "справедлив", "структур", "discipl", "order",
      "justice", "structure", "качество", "quality"),
     "mianxiang.json", ("five_elements", "metal")),
    (("стратег", "план", "идеализ", "рост", "развит", "strateg", "plan",
      "growth", "ideal"),
     "mianxiang.json", ("five_elements", "wood")),
    (("харизм", "вдохнов", "экспресс", "скорост", "charisma", "inspir",
      "speed", "expressive"),
     "mianxiang.json", ("five_elements", "fire")),
    (("надёжн", "надежн", "терпен", "практичн", "стабильн", "reliab",
      "patien", "practical", "steady"),
     "mianxiang.json", ("five_elements", "earth")),
    (("адаптив", "интуи", "гибк", "скрытн", "adapt", "intuit", "flexib"),
     "mianxiang.json", ("five_elements", "water")),
    (("избирательн", "глубин", "дистанц", "сдержан", "чувствительн",
      "selectiv", "depth", "reserved", "distan", "sensitiv"),
     "western.json", ("corman", "retracted")),
    (("общительн", "открыт", "широк", "sociab", "open", "extensive"),
     "western.json", ("corman", "dilated")),
    (("вязк", "несбиваем", "стойк", "память на несправедлив", "tenaci",
      "unshakeab", "выносл", "endur"),
     "western.json", ("kretschmer", "athletic")),
    (("абстрак", "отстранён", "утончённ", "abstract", "ascetic"),
     "western.json", ("kretschmer", "asthenic")),
]


def _load_kb(fname: str) -> dict:
    return json.loads((_KB_DIR / fname).read_text(encoding="utf-8"))


def reverse_physiognomy(
    traits: list[str], subject_type: str, locale: str = "ru",
) -> dict[str, Any]:
    """Map character traits → face features via the physiognomy KB (reverse).

    Ethics gate: `subject_type` MUST be "fictional" or "self". The KB
    ethics_note forbids reading third parties; the reverse direction
    inherits the same rule.
    """
    if subject_type not in ("fictional", "self"):
        raise ValueError(
            "ethics gate: reverse physiognomy is allowed only for "
            "subject_type 'fictional' or 'self' (never third parties)"
        )
    loc = "ru" if locale == "ru" else "en"
    kbs = {f: _load_kb(f) for f in ("mianxiang.json", "western.json")}

    matched: list[dict] = []
    seen: set[tuple[str, ...]] = set()
    unmatched: list[str] = []
    for trait in traits:
        t = trait.lower().strip()
        found = False
        for keywords, fname, path in _TRAIT_INDEX:
            if any(k in t for k in keywords):
                found = True
                if (fname, *path) in seen:
                    continue
                seen.add((fname, *path))
                node = kbs[fname]
                for key in path:
                    node = node[key]
                shape = node.get("shape", {})
                reading = node.get("reading", node)
                matched.append({
                    "trait": trait,
                    "system": fname.replace(".json", ""),
                    "type": path[-1],
                    "face_features": shape.get(loc) or shape.get("ru", ""),
                    "kb_reading": (reading.get(loc) or reading.get("ru", ""))
                    if isinstance(reading, dict) else "",
                    "source": node.get("source", ""),
                })
        if not found:
            unmatched.append(trait)

    feature_lines = [m["face_features"] for m in matched if m["face_features"]]
    return {
        "subject_type": subject_type,
        "matched": matched,
        "unmatched_traits": unmatched,
        "face_feature_seed": "; ".join(feature_lines),
        "kb_files": sorted({m["system"] + ".json" for m in matched}),
    }
