"""Tests for astrology provenance tracking (SWIEPH-only since WP-1)."""

import json
from datetime import datetime
from unittest.mock import Mock

import pytest

from backend.core import ephemeris as ephe_config
from backend.services.astrology import AstrologyService, ProvenanceInfo
from backend.services.astrology.ephemeris import SwissEphemeris


@pytest.fixture
def astrology_service():
    """Service with a mocked ephemeris instance.

    Provenance is process-level configuration (backend.core.ephemeris),
    so it must not depend on any state of the ephemeris object.
    """
    return AstrologyService(ephemeris=Mock(spec=SwissEphemeris))


def test_provenance_info_creation():
    provenance = ProvenanceInfo(
        ephemeris_engine=ephe_config.ENGINE_LABEL,
        ephemeris_version=ephe_config.EPHEMERIS_VERSION,
        calculation_timestamp=datetime(2026, 1, 1, 12, 0, 0),
        methodology="Placidus houses",
        accuracy_statement="≤0.2 arcsec vs JPL DE421",
    )

    assert "SWIEPH" in provenance.ephemeris_engine
    assert provenance.methodology == "Placidus houses"


def test_get_provenance_is_swieph(astrology_service):
    provenance = astrology_service._get_provenance()

    assert provenance is not None
    assert "SWIEPH" in provenance.ephemeris_engine
    assert "Swiss Ephemeris" in provenance.ephemeris_version
    assert "Placidus" in provenance.methodology
    assert "arcsec" in provenance.accuracy_statement


def test_get_provenance_never_mentions_moshier(astrology_service):
    """WP-1 acceptance: provenance reflects the actual source — the word
    Moshier must not appear anywhere in it."""
    blob = astrology_service._get_provenance().model_dump_json().lower()
    assert "moshier" not in blob
    assert "moseph" not in blob


def test_provenance_reports_real_swisseph_version(astrology_service):
    """The version string comes from swe.version, not a hardcoded guess."""
    provenance = astrology_service._get_provenance()
    assert ephe_config.SWE_VERSION in provenance.ephemeris_engine
    assert ephe_config.SWE_VERSION in provenance.ephemeris_version


def test_provenance_info_json_serialization():
    provenance = ProvenanceInfo(
        ephemeris_engine="Swiss Ephemeris 2.10.03 (SWIEPH)",
        ephemeris_version="Swiss Ephemeris 2.10.03 / JPL DE431 .se1 files (SWIEPH)",
        calculation_timestamp=datetime(2025, 1, 1, 12, 0, 0),
        methodology="Placidus houses",
        accuracy_statement="≤0.2 arcsec",
    )

    data = provenance.model_dump()
    assert data["ephemeris_engine"] == "Swiss Ephemeris 2.10.03 (SWIEPH)"

    parsed = json.loads(provenance.model_dump_json())
    assert parsed["ephemeris_version"].endswith("(SWIEPH)")
