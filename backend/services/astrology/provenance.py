"""Provenance helpers for deterministic astrology calculations."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .engine.ephemeris_engine import EphemerisConfig, EphemerisEngine


@dataclass
class TimeContext:
    timezone: str
    jd_ut: float
    dt_utc: str
    dt_local: str


@dataclass
class LocationContext:
    coords: dict
    coords_source: str
    geocoder: Optional[dict]


@dataclass
class Provenance:
    calculation_version: str
    ephemeris_engine: str
    ephemeris_files: list
    swe: dict
    time: TimeContext
    location: LocationContext

    def as_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["ephemeris_files"] = [asdict(f) for f in payload.get("ephemeris_files", [])]
        return payload


def _calculation_version() -> str:
    git_sha = os.getenv("GIT_COMMIT")
    version_file = Path("VERSION")
    semver = version_file.read_text().strip() if version_file.exists() else None
    if git_sha and semver:
        return f"git:{git_sha} | semver:{semver}"
    if git_sha:
        return f"git:{git_sha}"
    if semver:
        return f"semver:{semver}"
    return "semver:0.3.0"


def build_provenance(
    engine: EphemerisEngine,
    jd_ut: float,
    timezone_name: str,
    lat: float,
    lon: float,
    coords_source: str = "user",
    geocoder_meta: Optional[dict] = None,
) -> Provenance:
    dt_utc = datetime.fromtimestamp((jd_ut - 2440587.5) * 86400, tz=timezone.utc)
    dt_local = dt_utc.astimezone()
    ephe_config: EphemerisConfig = engine.config
    return Provenance(
        calculation_version=_calculation_version(),
        ephemeris_engine=ephe_config.ephemeris_engine,
        ephemeris_files=ephe_config.ephemeris_files,
        swe={"flags": ephe_config.flags_text, "house_system": "P", "ayanamsa": None},
        time=TimeContext(
            timezone=timezone_name,
            jd_ut=jd_ut,
            dt_utc=dt_utc.isoformat(),
            dt_local=dt_local.isoformat(),
        ),
        location=LocationContext(
            coords={"lat": lat, "lon": lon},
            coords_source=coords_source,
            geocoder=geocoder_meta,
        ),
    )
