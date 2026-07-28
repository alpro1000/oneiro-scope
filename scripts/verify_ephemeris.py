#!/usr/bin/env python3
"""WP-1 acceptance harness: our ephemeris vs a JPL-grade referee.

Referee: skyfield + JPL DE421 SPICE kernel (numerical integration —
the same family Swiss Ephemeris compresses). The kernel (~17 MB) is
fetched once into data/ephemeris_ref/ (gitignored) from the skyfield
project's CI mirror.

A first draft of this harness used astronomy-engine 2.1.19 as the
referee and showed 9–12″ "errors" on Saturn/Neptune in BOTH Swiss
modes. That exposed the referee, not Swiss: astronomy-engine's
truncated VSOP87 targets arc-minute accuracy on outer planets. The
July-2026 audit's "Neptune 13.55″ ⇒ Moshier" attribution came from the
same class of referee; against DE421 the SWIEPH agreement is ≤0.2″.

Prints geocentric apparent ecliptic-of-date longitude differences per
body for MOSEPH (pre-WP-1 fallback) and SWIEPH (repo-shipped .se1
files) against DE421, plus the astronomy-engine column for the record.

Usage:
    python scripts/verify_ephemeris.py [2026-07-28T12:00:00Z]
"""

from __future__ import annotations

import math
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import swisseph as swe

EPHE_DIR = REPO / "backend" / "data" / "ephemeris"
REF_DIR = REPO / "data" / "ephemeris_ref"
KERNEL = REF_DIR / "de421.bsp"
KERNEL_URL = (
    "https://raw.githubusercontent.com/skyfielders/python-skyfield/master/ci/de421.bsp"
)

BODIES = [
    ("Sun", swe.SUN, "sun", "Sun"),
    ("Moon", swe.MOON, "moon", "Moon"),
    ("Mercury", swe.MERCURY, "mercury", "Mercury"),
    ("Venus", swe.VENUS, "venus", "Venus"),
    ("Mars", swe.MARS, "mars barycenter", "Mars"),
    ("Jupiter", swe.JUPITER, "jupiter barycenter", "Jupiter"),
    ("Saturn", swe.SATURN, "saturn barycenter", "Saturn"),
    ("Uranus", swe.URANUS, "uranus barycenter", "Uranus"),
    ("Neptune", swe.NEPTUNE, "neptune barycenter", "Neptune"),
    ("Pluto", swe.PLUTO, "pluto barycenter", "Pluto"),
]

ACCEPTANCE_ARCSEC = 2.0  # WP-1: ≤2″ per body against the referee


def _ensure_kernel() -> Path:
    if KERNEL.exists():
        return KERNEL
    REF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"fetching DE421 kernel → {KERNEL} …")
    with urllib.request.urlopen(KERNEL_URL, timeout=120) as resp:
        KERNEL.write_bytes(resp.read())
    return KERNEL


def _arcsec(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0) * 3600.0


def main() -> int:
    iso = sys.argv[1] if len(sys.argv) > 1 else "2026-07-28T12:00:00Z"
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60 + dt.second / 3600)

    missing = [f for f in ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
               if not (EPHE_DIR / f).exists()]
    if missing:
        print(f"FAIL: ephemeris files missing from {EPHE_DIR}: {missing}")
        return 1
    swe.set_ephe_path(str(EPHE_DIR))

    from skyfield.api import load, load_file
    from skyfield import framelib

    eph = load_file(str(_ensure_kernel()))
    ts = load.timescale()
    t = ts.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    earth = eph["earth"]

    try:
        import astronomy  # optional context column

        ae_time = astronomy.Time.Make(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

        def ae_lon(body_name: str) -> float:
            vec = astronomy.GeoVector(getattr(astronomy.Body, body_name), ae_time, aberration=True)
            ecl = astronomy.RotateVector(astronomy.Rotation_EQJ_ECT(ae_time), vec)
            return math.degrees(math.atan2(ecl.y, ecl.x)) % 360.0
    except ImportError:
        ae_lon = None

    print(f"Instant: {dt.isoformat()}  (JD UT {jd:.6f})")
    print(f"swisseph {swe.version} · files: {EPHE_DIR}")
    print(f"referee: skyfield + JPL DE421\n")
    header = f"{'body':9} {'MOSEPH Δ″':>10} {'SWIEPH Δ″':>10} {'astronomy-engine Δ″':>20}"
    print(header)
    print("-" * len(header))

    worst = 0.0
    for name, code, sf_target, ae_name in BODIES:
        app = earth.at(t).observe(eph[sf_target]).apparent()
        _, lon, _ = app.frame_latlon(framelib.ecliptic_frame)
        ref = lon.degrees
        d_mos = _arcsec(swe.calc_ut(jd, code, swe.FLG_MOSEPH)[0][0], ref)
        d_swi = _arcsec(swe.calc_ut(jd, code, swe.FLG_SWIEPH)[0][0], ref)
        worst = max(worst, d_swi)
        ae_col = f"{_arcsec(ae_lon(ae_name), ref):20.2f}" if ae_lon else f"{'n/a':>20}"
        print(f"{name:9} {d_mos:10.2f} {d_swi:10.2f} {ae_col}")

    verdict = "PASS" if worst <= ACCEPTANCE_ARCSEC else "FAIL"
    print(f"\nworst SWIEPH deviation vs DE421: {worst:.2f}\" — {verdict} "
          f"(bar {ACCEPTANCE_ARCSEC}\")")
    return 0 if worst <= ACCEPTANCE_ARCSEC else 1


if __name__ == "__main__":
    raise SystemExit(main())
