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
    assert day_one.provenance["ephemeris_engine"] == "swisseph_swieph"
    assert day_one.provenance["flags"] == "SWIEPH|SPEED"


def test_provenance_carries_file_hashes_and_version():
    """WP-1: SWIEPH is the only mode — provenance must name the actual
    .se1 files (with hashes) and the real swisseph version."""
    result = compute_lunar("2024-02-01", "UTC")
    assert result.provenance["ephemeris_engine"] == "swisseph_swieph"
    assert result.provenance["ephemeris_files"], "Expected ephemeris file hashes"
    assert all(f["sha256"] for f in result.provenance["ephemeris_files"])
    assert result.provenance["swisseph_version"]
    assert result.provenance["flags"] == "SWIEPH|SPEED"

