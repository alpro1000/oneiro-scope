"""WP-1: SWIEPH is the only ephemeris mode — files ship, fallbacks are gone.

Acceptance criteria covered:
- the repo ships the required .se1 files and they are non-trivial;
- calc_ut actually uses SWIEPH (the returned flags carry the bit — this
  catches the C library silently substituting another source);
- an incomplete ephemeris directory raises instead of degrading;
- Chiron — absent from the analytic Moshier theory — computes from
  seas_18.se1;
- no backend module references FLG_MOSEPH anymore (structural);
- the exported provenance constants contain no Moshier wording.

Accuracy itself is checked against an independent JPL DE421 referee by
scripts/verify_ephemeris.py (needs a one-time ~17 MB kernel download, so
it stays a script, not a CI test): worst SWIEPH deviation 0.17″ / bar 2″.
"""

from datetime import datetime
from pathlib import Path

import pytest
import swisseph as swe

from backend.core import ephemeris as ephe_config

REPO = Path(__file__).resolve().parents[2]


def test_repo_ships_required_se1_files():
    for name in ephe_config.REQUIRED_FILES:
        path = ephe_config.DEFAULT_EPHE_DIR / name
        assert path.is_file(), f"{name} must ship in backend/data/ephemeris"
        assert path.stat().st_size > 100_000, f"{name} looks truncated"


def test_resolve_rejects_incomplete_dir(tmp_path):
    (tmp_path / "sepl_18.se1").write_bytes(b"x")  # semo/seas missing
    with pytest.raises(RuntimeError, match="missing"):
        ephe_config.resolve_ephe_dir(str(tmp_path))


def test_resolve_honours_env_alias(tmp_path, monkeypatch):
    for name in ephe_config.REQUIRED_FILES:
        (tmp_path / name).write_bytes(b"x")
    for var in ("SWISSEPH_EPHE_PATH", "SE_EPHE_PATH"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("SWISSEPH_PATH", str(tmp_path))
    assert ephe_config.resolve_ephe_dir() == tmp_path


def test_calc_ut_actually_uses_swieph():
    jd = swe.julday(2026, 7, 28, 12.0)
    for body in (swe.SUN, swe.MOON, swe.SATURN, swe.NEPTUNE, swe.CHIRON):
        _, ret_flags = swe.calc_ut(jd, body, ephe_config.FLAGS)
        assert ret_flags & swe.FLG_SWIEPH, f"body {body} not computed via SWIEPH"


def test_chiron_computes_from_asteroid_file():
    from backend.services.astrology.ephemeris import SwissEphemeris
    from backend.services.astrology.schemas import Planet

    data = SwissEphemeris().calculate_planet_position(
        Planet.CHIRON, datetime(2026, 7, 28, 12, 0, 0)
    )
    assert 0.0 <= data.longitude < 360.0
    assert data.distance > 5.0  # Chiron orbits between Saturn and Uranus


def test_no_module_references_moseph():
    """Structural: the MOSEPH flag is banned from backend code (tests aside)."""
    offenders = []
    for path in (REPO / "backend").rglob("*.py"):
        rel = path.relative_to(REPO)
        if "tests" in rel.parts or "external" in rel.parts:
            continue
        if "FLG_MOSEPH" in path.read_text(encoding="utf-8"):
            offenders.append(str(rel))
    assert not offenders, f"FLG_MOSEPH must not be used: {offenders}"


def test_engine_constants_have_no_moshier_wording():
    for value in (
        ephe_config.ENGINE_LABEL,
        ephe_config.EPHEMERIS_VERSION,
        ephe_config.ACCURACY_STATEMENT,
    ):
        assert "moshier" not in value.lower()
        assert "moseph" not in value.lower()


def test_ephemeris_files_provenance_hashes():
    files = ephe_config.ephemeris_files()
    assert len(files) == len(ephe_config.REQUIRED_FILES)
    for item in files:
        assert len(item["sha256"]) == 64
        assert item["size"] > 100_000
