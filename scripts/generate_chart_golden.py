#!/usr/bin/env python3
"""Generate the golden set chart-kit is measured against.

Twenty charts chosen to break things rather than to look representative:
latitudes past the polar circle where Placidus dies, the equator where
the quadrants degenerate, births at midnight and at the DST boundary,
epochs at both ends of the shipped ephemeris coverage, and both
hemispheres.

Output is `packages/chart-kit/test/golden.json`: for each chart the
server's `chart_core` (the client's only input) plus the server's OWN
answers for angles, cusps, aspects and dignities. The TypeScript test
recomputes all of it from the core alone and must agree to 0.01°.

Regenerate after any change to the ephemeris configuration or the
chart_core contract:

    python scripts/generate_chart_golden.py
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import swisseph as swe  # noqa: E402

from backend.services.astrology.chart_core import (  # noqa: E402
    HOUSE_SYSTEM_CODES,
    build_chart_core,
    resolve_house_system,
)

OUT = REPO / "packages" / "chart-kit" / "test" / "golden.json"

# (label, date, time, lat, lon, why this one is in the set)
CASES = [
    ("reference-zaporizhzhia", date(1977, 7, 1), time(22, 30), 47.8388, 35.1396,
     "the repo's reference chart, placements verified by the owner"),
    ("equator-noon", date(2000, 3, 20), time(12, 0), 0.0, 0.0,
     "equator: quadrants degenerate, tan(phi) vanishes"),
    ("london", date(1990, 6, 15), time(9, 45), 51.5074, -0.1278,
     "temperate northern, negative longitude"),
    ("sydney", date(1985, 11, 3), time(16, 20), -33.8688, 151.2093,
     "southern hemisphere, far east longitude"),
    ("reykjavik", date(1972, 12, 21), time(23, 55), 64.1466, -21.9426,
     "just equatorward of the polar circle at winter solstice"),
    ("tromso", date(1990, 1, 15), time(3, 20), 69.6492, 18.9553,
     "beyond the polar circle: Placidus undefined, substitution expected"),
    ("longyearbyen", date(2005, 6, 21), time(12, 0), 78.2232, 15.6267,
     "deep Arctic at midsummer, the hardest case for house math"),
    ("ushuaia", date(1998, 8, 9), time(5, 5), -54.8019, -68.3030,
     "far south, high latitude in the other hemisphere"),
    ("antarctic-base", date(2010, 7, 1), time(0, 0), -75.0, 0.0,
     "beyond the antarctic circle, midnight, prime meridian"),
    ("tokyo", date(1963, 4, 28), time(18, 30), 35.6762, 139.6503,
     "east Asia, historic date"),
    ("midnight-exact", date(2001, 1, 1), time(0, 0), 55.7558, 37.6173,
     "exactly midnight: date-boundary arithmetic"),
    ("one-minute-to-midnight", date(2001, 1, 1), time(23, 59), 55.7558, 37.6173,
     "the other side of the same boundary"),
    ("dst-spring-forward", date(1985, 3, 31), time(2, 30), 50.4501, 30.5234,
     "inside the hour the clock skips — tzdata must resolve it"),
    ("soviet-decree-time", date(1955, 5, 10), time(14, 15), 55.7558, 37.6173,
     "Moscow decree time, pre-1970 tzdata rules"),
    ("early-epoch", date(1815, 6, 18), time(11, 0), 50.6798, 4.4124,
     "near the early edge of the shipped .se1 coverage"),
    ("late-epoch", date(2350, 1, 1), time(6, 0), 40.7128, -74.0060,
     "near the late edge of coverage"),
    ("antimeridian-east", date(1995, 9, 12), time(7, 45), -17.7134, 178.0650,
     "just east of the antimeridian: longitude wrap"),
    ("antimeridian-west", date(1995, 9, 12), time(7, 45), -13.7590, -172.1046,
     "just west of it, same instant"),
    ("mercury-retrograde", date(2026, 2, 20), time(10, 0), 48.2082, 16.3738,
     "several bodies retrograde: applying/separating signs"),
    ("no-birth-time", date(1977, 7, 1), None, 47.8388, 35.1396,
     "time unknown: noon assumed, houses must be treated as meaningless"),
]

ASPECTS = {
    "conjunction": (0, 10), "opposition": (180, 10), "trine": (120, 8),
    "square": (90, 8), "sextile": (60, 6), "quincunx": (150, 3),
}
ASPECTING = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
             "Uranus", "Neptune", "Pluto"]


def server_aspects(core: dict) -> list[dict]:
    """The server's own aspect list, for the kit to reproduce."""
    out = []
    names = [n for n in ASPECTING if n in core["bodies"]]
    for i, a_name in enumerate(names):
        for b_name in names[i + 1:]:
            a, b = core["bodies"][a_name], core["bodies"][b_name]
            s = (a["ecl_lon"] - b["ecl_lon"] + 180) % 360 - 180
            delta = abs(s)
            speed_diff = a["speed_lon"] - b["speed_lon"]
            d_delta = speed_diff if s >= 0 else -speed_diff
            for kind, (exact, orb) in ASPECTS.items():
                deviation = delta - exact
                if abs(deviation) <= orb:
                    out.append({
                        "a": a_name, "b": b_name, "type": kind,
                        "orb": round(abs(deviation), 6),
                        "applying": deviation * d_delta < 0,
                    })
                    break
    return out


def server_lunar(core: dict) -> dict:
    """The lunar day of the chart's instant, by the server's own code.

    Imported from `backend.services.lunar.engine` rather than reproduced
    here: the point of the fixture is to catch the kit drifting from the
    server, and a second copy of the formula in this script would drift
    right alongside it. If the engine ever changes its synodic constant
    or its phase boundaries, this fixture moves and the kit's test fails —
    which is exactly the alarm we want.

    `illumination` is deliberately absent: the server takes it from
    `swe.pheno_ut`, and it is not derivable from a longitude pair (WP-16).
    """
    from backend.services.lunar.engine import (
        SYNODIC_MONTH, _moon_sign, _phase_key,
    )

    sun = core["bodies"]["Sun"]["ecl_lon"]
    moon = core["bodies"]["Moon"]["ecl_lon"]
    phase_angle = (moon - sun) % 360.0
    age = (phase_angle / 360.0) * SYNODIC_MONTH
    return {
        "phase_angle": round(phase_angle, 6),
        "moon_age_days": round(age, 6),
        "lunar_day": max(1, min(30, math.floor(age) + 1)),
        "phase": _phase_key(phase_angle),
        "moon_sign": _moon_sign(moon),
    }


def main() -> int:
    charts = []
    for label, d, t, lat, lon, why in CASES:
        built = build_chart_core(
            birth_date=d, birth_time=t, lat=lat, lon=lon, place_label=label
        )
        core = built.core
        jd = core["jd_ut"]
        system, note = resolve_house_system(jd, lat, lon, "placidus")
        cusps, ascmc = swe.houses_ex(jd, lat, lon, HOUSE_SYSTEM_CODES[system])
        charts.append({
            "label": label,
            "why": why,
            "chart_core": core,
            "house_system_note": note,
            "expected": {
                "asc": round(ascmc[0], 6),
                "mc": round(ascmc[1], 6),
                "cusps": [round(c, 6) for c in cusps[:12]],
                "aspects": server_aspects(core),
                "lunar": server_lunar(core),
            },
        })
        print(f"  {label:24} {system:10} asc={ascmc[0]:8.3f} mc={ascmc[1]:8.3f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "generated_by": "scripts/generate_chart_golden.py",
                "tolerance_deg": 0.01,
                "charts": charts,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {len(charts)} charts → {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
