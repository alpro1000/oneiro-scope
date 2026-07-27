"""Regression tests for the "City, Country" geocoding bug.

Found 2026-07 against the deployed MCP server: `validate_birth_data` with
`birth_place="Запорожье, Украина"` returned `valid: true, issues: []` and
coordinates 47.33333 / 36.26667 — a hamlet literally named «Україна», roughly
100 km from Zaporizhzhia (47.85 / 35.12). The same query without the country
suffix resolved correctly, which isolated the cause: the whole string went into
GeoNames' free-text `q` parameter instead of splitting the country out into
`country`.

Consequences on a natal chart computed from the wrong point: ASC +2.43 deg,
MC +1.08 deg, and the Moon flipped from house 12 to house 11 — all reported as
a successful validation. Three defects grew from that one root:

1. the country suffix polluted `q`;
2. `geonames_lookup` fetched 10 candidates "to choose best match" and then took
   `candidates[0]`, never choosing — GeoNames orders by relevance, so a hamlet
   can outrank a city of 700k;
3. the built-in fallback database was keyed on the full string, so
   "Запорожье, Украина" missed the "запорожье" entry too.
"""

from __future__ import annotations

import pytest

from backend.utils import geonames_resolver as gr
from backend.utils.geonames_resolver import (
    clear_cache,
    geonames_lookup,
    name_matches,
    pick_best,
    split_place_query,
)

# The two rows that actually caused the bug: GeoNames returned the hamlet first.
HAMLET = {
    "name": "Ukraina",
    "toponymName": "Ukraina",
    "countryName": "Украина",
    "lat": "47.33333",
    "lng": "36.26667",
    "population": 0,
    "geonameId": 1,
    "timezone": {"timeZoneId": "Europe/Kyiv"},
}
ZAPORIZHZHIA = {
    "name": "Запорожье",
    "toponymName": "Zaporizhzhia",
    "asciiName": "Zaporizhzhia",
    "countryName": "Украина",
    "lat": "47.85167",
    "lng": "35.11714",
    "population": 710052,
    "geonameId": 687700,
    "timezone": {"timeZoneId": "Europe/Kyiv"},
}


# ── query splitting ─────────────────────────────────────────────────────────

def test_splits_city_from_russian_country():
    city, code, raw = split_place_query("Запорожье, Украина")
    assert city == "Запорожье"
    assert code == "UA"
    assert raw == "Украина"


def test_splits_city_from_english_country():
    assert split_place_query("Prague, Czech Republic") == ("Prague", "CZ", "Czech Republic")
    assert split_place_query("Barcelona, España")[1] == "ES"


def test_no_comma_leaves_query_untouched():
    assert split_place_query("Запорожье") == ("Запорожье", None, None)


def test_unrecognised_tail_is_not_guessed_at():
    """An admin area is not a country — keep it in the query, do not invent a filter."""
    city, code, raw = split_place_query("Frankfurt am Main, Hessen")
    assert city == "Frankfurt am Main, Hessen"
    assert code is None and raw is None


def test_whitespace_and_case_tolerated():
    assert split_place_query("  Плзень ,  ЧЕХИЯ  ")[:2] == ("Плзень", "CZ")


# ── name matching ───────────────────────────────────────────────────────────

def test_hamlet_named_after_country_is_rejected():
    assert name_matches("Запорожье", HAMLET) is False


def test_city_matches_itself():
    assert name_matches("Запорожье", ZAPORIZHZHIA) is True


def test_match_survives_transliteration():
    """A Cyrillic request must match a Latin toponym for the same place."""
    assert name_matches("Запорожье", {"name": "Zaporizhzhia"}) is True
    assert name_matches("Москва", {"name": "Moscow", "alternateNames": [{"name": "Москва"}]}) is True


def test_different_city_is_rejected():
    assert name_matches("Запорожье", {"name": "Berlin"}) is False


# ── candidate selection ─────────────────────────────────────────────────────

def test_picks_the_city_not_the_first_row():
    """The exact failure: hamlet first, city second."""
    best, matched = pick_best([HAMLET, ZAPORIZHZHIA], "Запорожье")
    assert matched is True
    assert best["geonameId"] == 687700
    assert float(best["lat"]) == pytest.approx(47.85167)


def test_falls_back_to_population_and_flags_mismatch():
    small = dict(HAMLET, name="Nowhere", population=10)
    big = dict(HAMLET, name="Elsewhere", population=900_000)
    best, matched = pick_best([small, big], "Запорожье")
    assert matched is False, "nothing matched the requested city — must be flagged"
    assert best["name"] == "Elsewhere"


def test_pick_best_rejects_empty_candidates():
    with pytest.raises(ValueError):
        pick_best([], "Запорожье")


# ── end-to-end through geonames_lookup ──────────────────────────────────────

class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    """Records the params GeoNames would have been called with."""

    def __init__(self, payload):
        self._payload = payload
        self.calls: list[dict] = []

    async def get(self, url, params=None):
        self.calls.append(dict(params or {}))
        return _FakeResponse(self._payload)


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_cache()
    yield
    clear_cache()


@pytest.mark.asyncio
async def test_lookup_sends_country_param_and_returns_the_city(monkeypatch):
    fake = _FakeClient({"geonames": [HAMLET, ZAPORIZHZHIA]})
    monkeypatch.setattr(gr, "GEONAMES_USER", "test-user")
    monkeypatch.setattr(gr, "get_http_client", lambda: fake)

    result = await geonames_lookup("Запорожье, Украина")

    # The country went into its own parameter, not into the free-text query.
    assert fake.calls, "GeoNames was never called"
    sent = fake.calls[0]
    assert sent["q"] == "Запорожье"
    assert sent["country"] == "UA"

    # And the city won over the hamlet that used to be returned.
    assert result["resolved_name"] == "Запорожье"
    assert result["requested_city"] == "Запорожье"
    assert result["name_matched"] is True
    assert result["lat"] == pytest.approx(47.85167)
    assert result["lon"] == pytest.approx(35.11714)


@pytest.mark.asyncio
async def test_lookup_flags_a_suspicious_resolution(monkeypatch):
    """Resolution must never be silently wrong — the flag is the contract."""
    fake = _FakeClient({"geonames": [HAMLET]})
    monkeypatch.setattr(gr, "GEONAMES_USER", "test-user")
    monkeypatch.setattr(gr, "get_http_client", lambda: fake)

    result = await geonames_lookup("Запорожье, Украина")

    assert result["name_matched"] is False
    assert result["resolved_name"] == "Ukraina"


@pytest.mark.asyncio
async def test_fallback_database_hit_with_country_suffix(monkeypatch):
    """Without an API key the built-in city list must still find the city."""
    monkeypatch.setattr(gr, "GEONAMES_USER", None)

    result = await geonames_lookup("Запорожье, Украина")

    assert result["geonameId"] is None, "should come from the built-in database"
    assert result["name_matched"] is True
    assert 47.5 < result["lat"] < 48.2
    assert 34.8 < result["lon"] < 35.5
    assert result["timezone"] == "Europe/Kyiv"


@pytest.mark.asyncio
async def test_plain_city_query_unaffected(monkeypatch):
    """The form that already worked must keep working, with no country param."""
    fake = _FakeClient({"geonames": [ZAPORIZHZHIA]})
    monkeypatch.setattr(gr, "GEONAMES_USER", "test-user")
    monkeypatch.setattr(gr, "get_http_client", lambda: fake)

    result = await geonames_lookup("Запорожье")

    assert fake.calls[0]["q"] == "Запорожье"
    assert "country" not in fake.calls[0]
    assert result["name_matched"] is True
