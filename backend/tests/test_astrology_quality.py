import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from backend.services.astrology.engine.aspects import BodyState, detect_aspects
from backend.services.astrology.engine.ephemeris_engine import EphemerisEngine
from backend.services.astrology.engine.houses import HouseCalculator
from backend.services.astrology.geocoder import Geocoder, GeocodingError
from backend.services.astrology.provenance import build_provenance
from backend.services.astrology.validators.quality_gates import (
    QualityReport,
    detect_numeric_hallucination,
    validate_houses,
)


@pytest.fixture
def temp_ephe_dir(tmp_path: Path) -> Path:
    ephe = tmp_path / "ephe"
    ephe.mkdir()
    file_path = ephe / "sepl_18.se1"
    file_path.write_bytes(b"dummy ephemeris data")
    return ephe


def test_provenance_contains_hashes(temp_ephe_dir: Path):
    engine = EphemerisEngine(str(temp_ephe_dir))
    jd = engine.julday(2024, 1, 1, 0.0)
    prov = build_provenance(engine, jd, "UTC", 0.0, 0.0)
    files = prov.ephemeris_files
    assert files, "ephemeris files should be hashed"
    assert files[0].sha256


@pytest.mark.asyncio
async def test_strict_geocode_requires_place_query(monkeypatch):
    """Test that geocoder requires a valid place query."""
    geocoder = Geocoder()
    with pytest.raises(GeocodingError) as exc:
        await geocoder.geocode("")
    assert "PLACE_QUERY_REQUIRED" in str(exc.value)

    with pytest.raises(GeocodingError) as exc:
        await geocoder.geocode("   ")
    assert "PLACE_QUERY_REQUIRED" in str(exc.value)


def test_houses_null_without_birth_time():
    report = QualityReport()
    validate_houses(None, birth_time_present=False, report=report)
    assert "HOUSES_NOT_COMPUTED_NO_BIRTHTIME" in report.get("warnings", [])


def test_applying_separating_consistency():
    states = [
        BodyState(name="sun", longitude=10.0, speed=1.0),
        BodyState(name="moon", longitude=68.0, speed=-0.5),
    ]
    aspects = detect_aspects(states)
    sextiles = [a for a in aspects if a.aspect == "sextile"]
    assert sextiles, "Expected a sextile aspect"
    applying_flags = {a.applying for a in sextiles}
    assert applying_flags == {True} or applying_flags == {False}


def test_llm_numeric_hallucination_detection():
    computed = {"aspects": [{"orb": 2.0}]}
    hallucinations = detect_numeric_hallucination("orb is 5 degrees", computed)
    assert "5" in hallucinations


def test_ephemeris_engine_modes(temp_ephe_dir: Path, monkeypatch):
    engine_with_path = EphemerisEngine(str(temp_ephe_dir))
    assert engine_with_path.engine_mode == "swisseph_swieph"
    assert engine_with_path.config.flags_text == "SWIEPH|SPEED"

    monkeypatch.delenv("SWISSEPH_EPHE_PATH", raising=False)
    engine_no_path = EphemerisEngine(None)
    assert engine_no_path.engine_mode == "swisseph_moseph"
    assert engine_no_path.config.flags_text == "MOSEPH|SPEED"
