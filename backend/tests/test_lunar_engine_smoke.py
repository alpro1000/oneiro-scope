import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.lunar.engine import compute_lunar


def test_lunar_engine_changes_between_dates():
    day_one = compute_lunar("2024-01-01", "UTC")
    day_two = compute_lunar("2024-01-05", "UTC")

    assert (
        day_one.lunar_day != day_two.lunar_day
        or day_one.phase_angle != day_two.phase_angle
    ), "Lunar output must vary between dates"

    assert "jd_ut" in day_one.provenance
    assert day_one.provenance["ephemeris_engine"] in {"swisseph_swieph", "swisseph_moseph"}
    assert day_one.provenance["flags"] in {"SWIEPH|SPEED", "MOSEPH|SPEED"}


def test_ephemeris_alias(monkeypatch, tmp_path: Path):
    ephe_dir = tmp_path / "ephe"
    ephe_dir.mkdir()
    (ephe_dir / "sepl_18.se1").write_bytes(b"dummy data")

    monkeypatch.setenv("SWISSEPH_PATH", str(ephe_dir))
    monkeypatch.delenv("SWISSEPH_EPHE_PATH", raising=False)

    result = compute_lunar("2024-02-01", "UTC")
    assert result.provenance["ephemeris_engine"] == "swisseph_swieph"
    assert result.provenance["ephemeris_files"], "Expected ephemeris hashes when path is present"
    assert result.provenance["flags"] == "SWIEPH|SPEED"

