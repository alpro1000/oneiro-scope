"""Ephemeris engine — SWIEPH-only Swiss Ephemeris with provenance capture."""

from __future__ import annotations

from dataclasses import dataclass, field

import swisseph as swe

from backend.core import ephemeris as ephe_config


@dataclass
class EphemerisFileInfo:
    path: str
    sha256: str
    size: int


@dataclass
class EphemerisConfig:
    ephemeris_engine: str
    flags: int
    flags_text: str
    ephemeris_files: list[EphemerisFileInfo] = field(default_factory=list)


class EphemerisEngine:
    """Swiss Ephemeris in SWIEPH mode.

    Configuration (path, flags, file hashes) comes from
    backend.core.ephemeris, which verifies the .se1 files at import —
    there are no mode branches and no analytic fallback here
    (conventions.md §12).
    """

    def __init__(self):
        self.ephe_path = str(ephe_config.EPHE_DIR)
        self.config = EphemerisConfig(
            ephemeris_engine=ephe_config.ENGINE_MODE,
            flags=ephe_config.FLAGS,
            flags_text=ephe_config.FLAGS_TEXT,
            ephemeris_files=[
                EphemerisFileInfo(**item) for item in ephe_config.ephemeris_files()
            ],
        )

    @property
    def engine_mode(self) -> str:
        return self.config.ephemeris_engine

    def julday(self, year: int, month: int, day: int, ut: float) -> float:
        return swe.julday(year, month, day, ut)

    def calc_body(self, jd_ut: float, body: int, flags: int | None = None):
        return swe.calc_ut(jd_ut, body, flags or self.config.flags)

    def houses(self, jd_ut: float, lat: float, lon: float, house_system: str = "P"):
        return swe.houses_ex(jd_ut, lat, lon, b"P" if house_system == "P" else house_system.encode())
