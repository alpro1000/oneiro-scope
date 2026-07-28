"""`chart_core` — the one payload the server owes a client.

The working prototype proved the point: given sidereal time, obliquity
and each body's ecliptic + equatorial coordinates, a browser computes
Asc/MC/Desc/IC for ANY point on Earth, house cusps, aspects, dignities
and astrocartography lines by itself — no ephemeris, no network, no
cost. So the ephemeris is needed exactly once per chart, and everything
derived from natal positions is free thereafter.

That makes this module the product's spine:

- one builder, two transports (MCP tool and HTTP endpoint) — a
  divergence between them is a bug, enforced by test;
- everything computable from these numbers is deliberately NOT sent
  (South Node is the North Node + 180°, houses are a function of
  lat/lon, aspects are a function of longitudes);
- the payload is budgeted at 2 KB so it can ride in any response and
  be cached offline.

Sidereal time and obliquity are a matched pair: `gmst` carries Swiss
Ephemeris' APPARENT sidereal time (nutation included) and `obliquity`
is the TRUE obliquity. Mixing an apparent angle with a mean obliquity
(or vice versa) shifts the Midheaven by up to ~17″ — the pair must
travel together, which is why both live in the same object.
"""

from __future__ import annotations

import json
from datetime import date as date_cls, time as time_cls
from typing import Any, NamedTuple, Optional

import swisseph as swe

from backend.core import ephemeris as ephe_config
from backend.core.ephemeris import FLAGS, require_in_range
from backend.services.astrology.historic_tz import resolve_birth_moment
from backend.services.strategic.disclaimer import DISCLAIMERS, DISCLAIMER_RU

# Schema version of the chart_core object itself. Bump when a field's
# meaning changes; clients cache these payloads offline and need to know
# whether a stored chart is still readable by the current chart-kit.
CHART_CORE_VERSION = "1"

# Bodies whose positions cannot be derived from anything else in the
# payload. The South Node is deliberately absent: it is the North Node
# plus 180°, and sending a derivable number costs bytes for nothing.
BODIES: dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "TrueNode": swe.TRUE_NODE,
    "Chiron": swe.CHIRON,
}

# The node the chart is built on. Declared in the payload because the
# true/mean choice moves the node by up to ~1.8° — enough to change its
# house — and a client cannot tell which one it received from the number
# alone. (`backend/tests/test_node_definition_consistency.py` keeps every
# engine in the repo on the true node.)
NODE_TYPE = "true"

DEFAULT_HOUSE_SYSTEM = "placidus"

# Swiss Ephemeris house-system letters.
HOUSE_SYSTEM_CODES: dict[str, bytes] = {
    "placidus": b"P",
    "koch": b"K",
    "porphyry": b"O",
    "regiomontanus": b"R",
    "campanus": b"C",
    "equal": b"E",
    "whole_sign": b"W",
}

# Beyond the polar circle the time-based quadrant systems (Placidus,
# Koch) are mathematically undefined — points of the ecliptic never
# cross the horizon there, so there is no time to trisect, and Swiss
# Ephemeris refuses outright. Porphyry is the substitution: it keeps the
# quadrant structure Placidus users expect (cusp 1 = Asc, cusp 10 = MC)
# and merely trisects each quadrant evenly, so nothing about the chart's
# frame changes except the interior cusps. Whole-sign would change the
# logic itself, which is a bigger silent lie.
#
# The substitution is NEVER silent (conventions.md §12): the payload
# declares the system actually used plus the reason. Note that the four
# ANGLES stay valid at any latitude — they are pure trigonometry — so a
# polar chart loses its Placidus cusps, not its Ascendant.
POLAR_FALLBACK_SYSTEM = "porphyry"

# Budget, in bytes of compact JSON. Not a soft target: the payload rides
# in every response and gets stored offline, so growth has to be an
# explicit decision, not a drift.
CHART_CORE_MAX_BYTES = 2048


class ChartCore(NamedTuple):
    """The budgeted core plus the prose that explains it, kept apart.

    `core` is what the client computes from and caches offline;
    `house_system_note` is present only when the requested house system
    was undefined at this latitude and had to be substituted.
    """

    core: dict[str, Any]
    house_system_note: Optional[str] = None


def _equatorial_flags() -> int:
    return swe.FLG_SWIEPH | swe.FLG_EQUATORIAL


def resolve_house_system(
    jd_ut: float, lat: float, lon: float, requested: str = DEFAULT_HOUSE_SYSTEM
) -> tuple[str, Optional[str]]:
    """Return the house system usable at this location, and why it changed.

    The boundary is taken from the library, not from a hardcoded polar
    circle: we ask Swiss Ephemeris to compute, and treat its refusal as
    the definition of "undefined here". The obliquity — hence the
    boundary — drifts with the epoch, so asking beats guessing.

    Returns (system_name, substitution_reason). The reason is None when
    the requested system worked.
    """
    requested = requested.lower()
    code = HOUSE_SYSTEM_CODES.get(requested)
    if code is None:
        # Checked here rather than left to the library: an unknown letter
        # makes swe.houses_ex fall back to Porphyry SILENTLY and return a
        # normal-looking tuple, so a typo would produce a wrong-system
        # chart with nothing to show for it.
        raise ValueError(
            f"Unknown house system {requested!r}; known: "
            f"{', '.join(sorted(HOUSE_SYSTEM_CODES))}"
        )
    # Coordinate sanity is checked BEFORE calling, because swe.Error is
    # raised both for a polar Placidus and for an out-of-range latitude.
    # Narrowing the except clause alone would not tell those apart — a
    # caller passing lat=500 would be answered with a polar-circle
    # explanation. Validating first is what makes the except meaningful.
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude {lat} is outside [-90, 90]")
    if not -180.0 <= lon <= 360.0:
        raise ValueError(f"longitude {lon} is outside [-180, 360]")
    try:
        swe.houses_ex(jd_ut, lat, lon, code)
        return requested, None
    except swe.Error:
        # At a valid coordinate this genuinely is the undefined-quadrant
        # case; anything else propagates.
        fallback = POLAR_FALLBACK_SYSTEM
        swe.houses_ex(jd_ut, lat, lon, HOUSE_SYSTEM_CODES[fallback])
        return fallback, (
            f"{requested} is undefined at latitude {lat:.4f} (beyond the polar "
            f"circle no ecliptic point crosses the horizon, so there is no "
            f"diurnal arc to divide); using {fallback}, which keeps cusp 1 = "
            f"Asc and cusp 10 = MC. The four angles are unaffected."
        )


def _body_state(jd_ut: float, code: int, name: str) -> dict[str, Any]:
    """Ecliptic + equatorial state of one body, verified SWIEPH.

    Two calls per body: the ecliptic one carries longitude, latitude and
    speed; the equatorial one carries right ascension and declination,
    which the client needs for astrocartography loci (they are not
    recoverable from longitude alone without also knowing latitude AND
    doing the rotation — sending them is cheaper than making every
    client repeat it).
    """
    ecl, ret_ecl = swe.calc_ut(jd_ut, code, FLAGS)
    equ, ret_equ = swe.calc_ut(jd_ut, code, _equatorial_flags())
    for ret in (ret_ecl, ret_equ):
        if not ret & swe.FLG_SWIEPH:
            raise RuntimeError(
                f"Swiss Ephemeris did not use SWIEPH for {name} "
                f"(returned flags {ret}) — refusing to label the payload SWIEPH"
            )
    return {
        "ecl_lon": round(ecl[0], 4),
        "ecl_lat": round(ecl[1], 4),
        "ra": round(equ[0], 4),
        "dec": round(equ[1], 4),
        "speed_lon": round(ecl[3], 4),
        "retrograde": ecl[3] < 0,
    }


def build_chart_core(
    *,
    birth_date: date_cls,
    birth_time: Optional[time_cls],
    lat: float,
    lon: float,
    place_label: str = "",
    timezone_name: Optional[str] = None,
    house_system: str = DEFAULT_HOUSE_SYSTEM,
) -> dict[str, Any]:
    """Build the self-contained chart payload.

    Args:
        birth_date: Local calendar date of birth.
        birth_time: Local clock time; None means noon is used and the
            client must treat houses/angles as unavailable.
        lat, lon: Birth coordinates (decimal degrees, east/north positive).
        place_label: Human label for the birth place — display only, it
            never participates in the computation.
        timezone_name: IANA zone override; omitted, the zone is derived
            from the coordinates via tzdata (historical rules included).
        house_system: Declared for the client; cusps themselves are the
            client's to compute.

    Returns the `chart_core` object (not the response envelope).
    """
    require_in_range(birth_date, "birth_date")
    moment = resolve_birth_moment(
        birth_date, birth_time, lat=lat, lon=lon, timezone_name=timezone_name
    )
    jd_ut = moment.jd_ut

    # Apparent sidereal time in degrees, paired with true obliquity below.
    gmst = swe.sidtime(jd_ut) * 15.0
    obliquity = swe.calc_ut(jd_ut, swe.ECL_NUT, swe.FLG_SWIEPH)[0][0]

    local_clock = f"{birth_date.isoformat()}T{(birth_time or time_cls(12, 0)).isoformat()}"
    system_used, substitution = resolve_house_system(jd_ut, lat, lon, house_system)

    core: dict[str, Any] = {
        "version": CHART_CORE_VERSION,
        "jd_ut": round(jd_ut, 6),
        "gmst": round(gmst % 360.0, 4),
        "obliquity": round(obliquity, 5),
        "birth": {
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "tz_used": moment.timezone_name,
            "utc_offset_used": _format_offset(moment.utc_offset_hours),
            "tz_source": moment.source,
            "local_clock": local_clock,
            "utc": moment.utc_iso,
            "place_label": place_label,
            "time_known": birth_time is not None,
        },
        "bodies": {
            name: _body_state(jd_ut, code, name) for name, code in BODIES.items()
        },
        "node_type": NODE_TYPE,
        "house_system": system_used,
    }
    # The substitution REASON is prose, not arithmetic: it rides in the
    # envelope, not in the budgeted core, so a long explanation can never
    # eat the bytes the numbers need.
    return ChartCore(core=core, house_system_note=substitution)


def build_chart_response(
    *,
    birth_date: date_cls,
    birth_time: Optional[time_cls],
    lat: float,
    lon: float,
    place_label: str = "",
    timezone_name: Optional[str] = None,
    house_system: str = DEFAULT_HOUSE_SYSTEM,
    locale: str = "ru",
) -> dict[str, Any]:
    """The complete response body — identical for MCP and HTTP.

    Both transports call exactly this: the MCP tool wraps it in nothing,
    the HTTP endpoint returns it as-is. A divergence between the two
    surfaces would mean a client behaves differently depending on how it
    reached the same server, so `test_chart_core_contract.py` asserts the
    two are byte-identical for the same input.

    The `meta` block is attached by the MCP layer's `with_meta` wrapper
    on that transport; the HTTP layer attaches the same block explicitly,
    so both carry request provenance.
    """
    built = build_chart_core(
        birth_date=birth_date,
        birth_time=birth_time,
        lat=lat,
        lon=lon,
        place_label=place_label,
        timezone_name=timezone_name,
        house_system=house_system,
    )
    body: dict[str, Any] = {
        "chart_core": built.core,
        "provenance": {
            "ephemeris_engine": ephe_config.ENGINE_LABEL,
            "ephemeris_version": ephe_config.EPHEMERIS_VERSION,
            "accuracy": ephe_config.ACCURACY_STATEMENT,
            "sidereal_time": "apparent (paired with true obliquity)",
        },
        "how_to_read": (
            "Everything derivable from these numbers — angles and house cusps "
            "for ANY location, aspects, dignities, astrocartography lines — is "
            "computed client-side by packages/chart-kit. No further server "
            "call is needed to explore this chart."
        ),
        "disclaimer": DISCLAIMERS.get(locale, DISCLAIMER_RU),
    }
    if built.house_system_note:
        body["house_system_note"] = built.house_system_note
    return body


def _format_offset(hours: float) -> str:
    """UTC offset as ±HH:MM — the field users argue about most.

    Half-hour and 45-minute zones (India, Nepal, Chatham) make a bare
    number ambiguous to read, so it ships pre-formatted.
    """
    sign = "-" if hours < 0 else "+"
    total_minutes = int(round(abs(hours) * 60))
    return f"{sign}{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def chart_core_bytes(core: dict[str, Any]) -> int:
    """Size of the payload as compact JSON — what the wire actually costs."""
    return len(json.dumps(core, separators=(",", ":"), ensure_ascii=False).encode())
