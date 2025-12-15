"""Ephemeris engine with deterministic Swiss Ephemeris configuration."""

from __future__ import annotations

import glob
import hashlib
import os
from dataclasses import dataclass, field
from typing import Iterable, Optional

import swisseph as swe

EPHE_PATTERNS = (
    "sepl*.se*",
    "sem*.se*",
    "seas*.se*",
    "semo*.se*",
)


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
    """Configure Swiss Ephemeris with swieph/moseph modes and capture provenance."""

    def __init__(self, ephe_path: Optional[str] = None):
        self.ephe_path = ephe_path or os.getenv("SWISSEPH_EPHE_PATH") or os.getenv("SE_EPHE_PATH")
        self.config = self._configure()

    def _configure(self) -> EphemerisConfig:
        engine_mode = "swisseph_moseph"
        ephe_files: list[EphemerisFileInfo] = []
        if self.ephe_path and os.path.isdir(self.ephe_path):
            swe.set_ephe_path(self.ephe_path)
            engine_mode = "swisseph_swieph"
            ephe_files = list(self._hash_ephemeris_files(self.ephe_path))
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        flags_text = "SWIEPH|SPEED"
        return EphemerisConfig(engine_mode, flags, flags_text, ephe_files)

    @staticmethod
    def _hash_ephemeris_files(path: str) -> Iterable[EphemerisFileInfo]:
        for pattern in EPHE_PATTERNS:
            for filename in glob.glob(os.path.join(path, pattern)):
                size = os.path.getsize(filename)
                with open(filename, "rb") as handle:
                    sha = hashlib.sha256(handle.read()).hexdigest()
                yield EphemerisFileInfo(path=filename, sha256=sha, size=size)

    @property
    def engine_mode(self) -> str:
        return self.config.ephemeris_engine

    def julday(self, year: int, month: int, day: int, ut: float) -> float:
        return swe.julday(year, month, day, ut)

    def calc_body(self, jd_ut: float, body: int, flags: Optional[int] = None):
        return swe.calc_ut(jd_ut, body, flags or self.config.flags)

    def houses(self, jd_ut: float, lat: float, lon: float, house_system: str = "P"):
        return swe.houses_ex(jd_ut, lat, lon, b"P" if house_system == "P" else house_system.encode())

