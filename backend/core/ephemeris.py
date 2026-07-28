"""Canonical Swiss Ephemeris configuration — SWIEPH only (WP-1).

One source of truth for the ephemeris mode. The repo ships the compressed
JPL files (backend/data/ephemeris/*.se1, DE431 basis), the path is set
exactly once at import, and every calculation module takes its flags from
here. There is no Moshier fallback on any data path: missing or incomplete
files raise at import, so the FastAPI app and the MCP server refuse to
start rather than silently degrade (conventions.md §12).

Accuracy is checked against an independent JPL-grade referee
(skyfield + DE421) by scripts/verify_ephemeris.py — worst SWIEPH
deviation across all 10 bodies is 0.17″ (Moon) against a 2″ bar.
"""

from __future__ import annotations

import hashlib
import os
from datetime import date
from functools import lru_cache
from pathlib import Path

import swisseph as swe

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EPHE_DIR = REPO_ROOT / "backend" / "data" / "ephemeris"

# Minimum SWIEPH set for 1800–2400 AD: planets, Moon, main asteroids
# (Chiron lives in seas_18.se1).
REQUIRED_FILES = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")

_ENV_VARS = ("SWISSEPH_EPHE_PATH", "SWISSEPH_PATH", "SE_EPHE_PATH")


def resolve_ephe_dir(explicit: str | None = None) -> Path:
    """Resolve and verify the ephemeris directory.

    Order: explicit argument → env override → repo default. Raises
    RuntimeError when any required .se1 file is absent — an incomplete
    directory must never silently downgrade the engine.
    """
    candidate = explicit or next(
        (os.getenv(var) for var in _ENV_VARS if os.getenv(var)), None
    )
    directory = Path(candidate) if candidate else DEFAULT_EPHE_DIR
    missing = [name for name in REQUIRED_FILES if not (directory / name).is_file()]
    if missing:
        raise RuntimeError(
            f"Swiss Ephemeris data files missing from {directory}: {missing}. "
            "SWIEPH is the only supported mode — restore backend/data/ephemeris "
            "or point SWISSEPH_EPHE_PATH at a complete set."
        )
    return directory


EPHE_DIR: Path = resolve_ephe_dir()
swe.set_ephe_path(str(EPHE_DIR))

FLAGS: int = swe.FLG_SWIEPH | swe.FLG_SPEED
FLAGS_TEXT = "SWIEPH|SPEED"
ENGINE_MODE = "swisseph_swieph"
SWE_VERSION: str = swe.version
ENGINE_LABEL = f"Swiss Ephemeris {SWE_VERSION} (SWIEPH)"
EPHEMERIS_VERSION = f"Swiss Ephemeris {SWE_VERSION} / JPL DE431 .se1 files (SWIEPH)"
ACCURACY_STATEMENT = (
    "≤0.2 arcsec vs independent JPL DE421 referee for all 10 bodies "
    "(scripts/verify_ephemeris.py); no analytic fallback — missing data "
    "files fail startup"
)

# Declared coverage of the shipped *_18.se1 set. Dates outside get a clean
# validation error at the input boundary instead of a deep swisseph error.
EPHE_MIN_DATE = date(1800, 1, 1)
EPHE_MAX_DATE = date(2399, 12, 31)


def require_in_range(when: date, context: str) -> None:
    """Reject dates outside the shipped ephemeris coverage, loudly."""
    if not (EPHE_MIN_DATE <= when <= EPHE_MAX_DATE):
        raise ValueError(
            f"{context}: {when.isoformat()} is outside the shipped Swiss "
            f"Ephemeris coverage {EPHE_MIN_DATE.isoformat()}"
            f"–{EPHE_MAX_DATE.isoformat()} (*_18.se1). Install files for "
            "that range and point SWISSEPH_EPHE_PATH at them."
        )


def calc_ut_swieph(jd_ut: float, body: int) -> tuple:
    """swe.calc_ut that REFUSES a silently substituted source.

    The C library can swap in another ephemeris when a body's file is
    unreadable and still return a result; the returned flags are the only
    witness. Every caller that labels its output SWIEPH must go through
    here (or perform the same check).
    """
    result, ret_flags = swe.calc_ut(jd_ut, body, FLAGS)
    if not ret_flags & swe.FLG_SWIEPH:
        raise RuntimeError(
            f"Swiss Ephemeris did not use SWIEPH for body {body} "
            f"(returned flags {ret_flags}) — check {EPHE_DIR}"
        )
    return result


def _startup_probe() -> None:
    """Prove the ACTIVE directory actually computes, at import.

    Filename presence alone admits truncated or tampered files; this runs
    one real calculation per data file (Sun→sepl, Moon→semo, Chiron→seas)
    and verifies the returned flags, so a broken set fails the process
    at startup instead of at the first user request.
    """
    j2000 = 2451545.0
    for body in (swe.SUN, swe.MOON, swe.CHIRON):
        calc_ut_swieph(j2000, body)


_startup_probe()


@lru_cache(maxsize=1)
def ephemeris_files() -> tuple[dict, ...]:
    """sha256 provenance for the shipped .se1 files (hashed once)."""
    out = []
    for name in REQUIRED_FILES:
        path = EPHE_DIR / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out.append(
            {"path": str(path), "sha256": digest, "size": path.stat().st_size}
        )
    return tuple(out)


def startup_summary() -> dict:
    """Live ephemeris configuration for /health and startup logs."""
    return {
        "engine": "SWIEPH",
        "swisseph_version": SWE_VERSION,
        "ephe_path": str(EPHE_DIR),
        "files": [Path(item["path"]).name for item in ephemeris_files()],
    }
