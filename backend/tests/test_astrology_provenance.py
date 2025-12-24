"""Tests for astrology provenance tracking (Phase 2)."""

import pytest
from datetime import date, time
from unittest.mock import Mock, AsyncMock, patch

from backend.services.astrology import AstrologyService, NatalChartRequest, ProvenanceInfo
from backend.services.astrology.ephemeris import SwissEphemeris


@pytest.fixture
def mock_ephemeris():
    """Mock Swiss Ephemeris."""
    ephemeris = Mock(spec=SwissEphemeris)
    ephemeris._engine_mode = "moseph"
    return ephemeris


@pytest.fixture
def astrology_service(mock_ephemeris):
    """Astrology service with mocked ephemeris."""
    service = AstrologyService(ephemeris=mock_ephemeris)
    return service


def test_provenance_info_creation():
    """Test ProvenanceInfo model creation."""
    from datetime import datetime

    provenance = ProvenanceInfo(
        ephemeris_engine="Moshier Algorithm (MOSEPH)",
        ephemeris_version="Swiss Ephemeris 2.10+",
        calculation_timestamp=datetime.utcnow(),
        methodology="Placidus houses",
        accuracy_statement="<1 arc second for modern dates"
    )

    assert provenance.ephemeris_engine == "Moshier Algorithm (MOSEPH)"
    assert provenance.ephemeris_version == "Swiss Ephemeris 2.10+"
    assert provenance.methodology == "Placidus houses"
    assert provenance.accuracy_statement == "<1 arc second for modern dates"


def test_get_provenance_moseph(astrology_service):
    """Test provenance generation for MOSEPH engine."""
    provenance = astrology_service._get_provenance()

    assert provenance is not None
    assert "MOSEPH" in provenance.ephemeris_engine
    assert "Swiss Ephemeris" in provenance.ephemeris_version
    assert "Placidus" in provenance.methodology
    assert "arc second" in provenance.accuracy_statement


def test_get_provenance_swieph():
    """Test provenance generation for SWIEPH engine."""
    mock_ephemeris = Mock(spec=SwissEphemeris)
    mock_ephemeris._engine_mode = "swieph"

    service = AstrologyService(ephemeris=mock_ephemeris)
    provenance = service._get_provenance()

    assert "SWIEPH" in provenance.ephemeris_engine
    assert "Swiss Ephemeris" in provenance.ephemeris_version


# Note: Integration test for natal_chart_includes_provenance would require
# mocking complex ephemeris calculations. The provenance functionality is
# tested indirectly through the service's _get_provenance() method tests above.


def test_provenance_info_json_serialization():
    """Test that ProvenanceInfo can be serialized to JSON."""
    from datetime import datetime

    provenance = ProvenanceInfo(
        ephemeris_engine="Moshier Algorithm (MOSEPH)",
        ephemeris_version="Swiss Ephemeris 2.10+",
        calculation_timestamp=datetime(2025, 1, 1, 12, 0, 0),
        methodology="Placidus houses",
        accuracy_statement="<1 arc second"
    )

    # Test model_dump (Pydantic v2)
    data = provenance.model_dump()
    assert data["ephemeris_engine"] == "Moshier Algorithm (MOSEPH)"
    assert data["ephemeris_version"] == "Swiss Ephemeris 2.10+"

    # Test JSON serialization
    import json
    json_str = provenance.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["ephemeris_engine"] == "Moshier Algorithm (MOSEPH)"
