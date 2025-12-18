"""Tests for GeoNames resolver utility."""

import os
import pytest
from backend.utils.geonames_resolver import (
    geonames_lookup,
    detect_language,
    transliterate_russian,
    clear_cache,
)

# Skip tests that require real GeoNames API unless GEONAMES_USERNAME is set
GEONAMES_AVAILABLE = os.getenv("GEONAMES_USERNAME", "demo") != "demo"
requires_geonames = pytest.mark.skipif(
    not GEONAMES_AVAILABLE,
    reason="Requires GEONAMES_USERNAME env var for real API access"
)


@requires_geonames
@pytest.mark.asyncio
async def test_geonames_lookup_latin():
    """Test GeoNames lookup with Latin city name."""
    result = await geonames_lookup("Moscow")

    assert result["input"] == "Moscow"
    assert result["resolved_name"] == "Moscow"
    assert result["country"] == "Russia"
    assert 55.0 < result["lat"] < 56.0  # Moscow latitude ~55.75
    assert 37.0 < result["lon"] < 38.0  # Moscow longitude ~37.62
    assert result["geonameId"] is not None


@requires_geonames
@pytest.mark.asyncio
async def test_geonames_lookup_russian():
    """Test GeoNames lookup with Russian city name."""
    result = await geonames_lookup("Москва")

    assert result["input"] == "Москва"
    assert result["resolved_name"] == "Moscow"
    assert result["country"] == "Russia"
    assert 55.0 < result["lat"] < 56.0
    assert 37.0 < result["lon"] < 38.0


@requires_geonames
@pytest.mark.asyncio
async def test_geonames_lookup_multilang_consistency():
    """Test that Russian and Latin names resolve to same location."""
    ru = await geonames_lookup("Санкт-Петербург")
    en = await geonames_lookup("Saint Petersburg")

    # Should resolve to same coordinates (within 0.1 degree)
    assert abs(ru["lat"] - en["lat"]) < 0.1
    assert abs(ru["lon"] - en["lon"]) < 0.1
    assert ru["country"] == en["country"] == "Russia"


@requires_geonames
@pytest.mark.asyncio
async def test_geonames_lookup_not_found():
    """Test GeoNames lookup with invalid place name."""
    with pytest.raises(ValueError, match="Place not found"):
        await geonames_lookup("NonexistentCityName12345")


@requires_geonames
@pytest.mark.asyncio
async def test_geonames_cache():
    """Test that GeoNames results are cached."""
    clear_cache()

    # First lookup
    result1 = await geonames_lookup("Paris")

    # Second lookup (should use cache)
    result2 = await geonames_lookup("Paris")

    assert result1 == result2
    assert result1["resolved_name"] == "Paris"
    assert result1["country"] == "France"


def test_detect_language_russian():
    """Test language detection for Russian text."""
    assert detect_language("Москва") == "ru"
    assert detect_language("Санкт-Петербург") == "ru"


def test_detect_language_latin():
    """Test language detection for Latin text."""
    assert detect_language("Moscow") == "en"
    assert detect_language("Saint Petersburg") == "en"
    assert detect_language("Paris") == "en"


def test_transliterate_russian():
    """Test Russian to Latin transliteration."""
    assert transliterate_russian("Москва") == "Moskva"
    assert transliterate_russian("Санкт-Петербург") == "Sankt-Peterburg"
    assert transliterate_russian("Новосибирск") == "Novosibirsk"

    # Mixed case
    assert transliterate_russian("МОСКВА") == "MOSKVA"

    # Already Latin (should pass through)
    assert transliterate_russian("Moscow") == "Moscow"


@requires_geonames
@pytest.mark.asyncio
async def test_geonames_lookup_european_cities():
    """Test GeoNames with various European cities."""
    cities = {
        "Praha": ("Prague", "Czechia"),
        "Berlin": ("Berlin", "Germany"),
        "London": ("London", "United Kingdom"),
    }

    for input_name, (expected_name, expected_country) in cities.items():
        result = await geonames_lookup(input_name)
        assert result["resolved_name"] == expected_name
        assert result["country"] == expected_country
