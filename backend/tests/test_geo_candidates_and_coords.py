"""Caller-supplied coordinates and candidate disambiguation.

Both come from one observation: when the service is reached through a chat
client, that client already reads any script (北京, القاهرة) and can ask the user
*which* Barcelona they mean. Geocoding a place the caller has already resolved
adds a guess where none is needed, and choosing silently between several
plausible places is the exact failure this module was fixed for.

So: `calculate_natal_chart` accepts lat/lon and skips geocoding, while
`search_city` surfaces the candidate pool it already paid for instead of
discarding it. Timezone stays out of the caller's hands — see the tz tests.
"""

from __future__ import annotations

from datetime import date as date_cls

import pytest

from backend.services.astrology.schemas import NatalChartRequest
from backend.utils.geonames_resolver import (
    clear_cache,
    geonames_lookup,
    is_ambiguous,
    trim_candidate,
)
from backend.utils import geonames_resolver as gr

BARCELONA_ES = {
    "name": "Barcelona", "toponymName": "Barcelona", "countryName": "Spain",
    "adminName1": "Catalonia", "lat": "41.38879", "lng": "2.15899",
    "population": 1620343, "fcode": "PPLA", "geonameId": 3128760,
    "timezone": {"timeZoneId": "Europe/Madrid"},
}
BARCELONA_VE = {
    "name": "Barcelona", "toponymName": "Barcelona", "countryName": "Venezuela",
    "adminName1": "Anzoátegui", "lat": "10.13624", "lng": "-64.68618",
    "population": 424795, "fcode": "PPLA", "geonameId": 3648522,
    "timezone": {"timeZoneId": "America/Caracas"},
}
ZAPORIZHZHIA = {
    "name": "Запорожье", "toponymName": "Zaporizhzhia", "countryName": "Украина",
    "adminName1": "Zaporizhzhia Oblast", "lat": "47.85167", "lng": "35.11714",
    "population": 710052, "fcode": "PPLA", "geonameId": 687700,
    "timezone": {"timeZoneId": "Europe/Kyiv"},
}


# ── ambiguity detection ─────────────────────────────────────────────────────

def test_same_name_in_two_countries_is_ambiguous():
    assert is_ambiguous([BARCELONA_ES, BARCELONA_VE], "Barcelona") is True


def test_single_match_is_not_ambiguous():
    assert is_ambiguous([ZAPORIZHZHIA], "Запорожье") is False


def test_unrelated_extra_candidates_do_not_create_ambiguity():
    """Only candidates that actually match the requested name count."""
    noise = dict(BARCELONA_VE, name="Berlin", toponymName="Berlin")
    assert is_ambiguous([BARCELONA_ES, noise], "Barcelona") is False


def test_trim_candidate_keeps_what_a_human_needs_to_choose():
    row = trim_candidate(BARCELONA_VE)
    assert row["name"] == "Barcelona"
    assert row["country"] == "Venezuela"
    assert row["admin_area"] == "Anzoátegui"
    assert row["population"] == 424795
    assert row["geonameId"] == 3648522
    assert row["lat"] == pytest.approx(10.13624)


# ── candidates reach the caller ─────────────────────────────────────────────

class _FakeResponse:
    # status_code matters: the resolver logs it on the primary path. Omitting it
    # made the primary call raise AttributeError and the tests silently passed
    # through the transliteration retry instead — validating the right values
    # via the wrong code path.
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.call_count = 0

    async def get(self, url, params=None):
        self.call_count += 1
        return _FakeResponse(self._payload)


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_cache()
    yield
    clear_cache()


@pytest.mark.asyncio
async def test_lookup_returns_candidates_without_extra_api_calls(monkeypatch):
    """The pool was always fetched (maxRows=10); it must not cost a second call."""
    fake = _FakeClient({"geonames": [BARCELONA_ES, BARCELONA_VE]})
    monkeypatch.setattr(gr, "GEONAMES_USER", "test-user")
    monkeypatch.setattr(gr, "get_http_client", lambda: fake)

    result = await geonames_lookup("Barcelona")

    assert fake.call_count == 1, "candidates must reuse the request already made"
    assert result["ambiguous"] is True
    assert len(result["candidates"]) == 2
    assert {c["country"] for c in result["candidates"]} == {"Spain", "Venezuela"}
    # Still returns a best pick — the flag tells the caller to confirm it.
    assert result["resolved_name"] == "Barcelona"
    assert result["lat"] == pytest.approx(41.38879), "most populous wins the pick"


@pytest.mark.asyncio
async def test_unambiguous_lookup_is_not_flagged(monkeypatch):
    fake = _FakeClient({"geonames": [ZAPORIZHZHIA]})
    monkeypatch.setattr(gr, "GEONAMES_USER", "test-user")
    monkeypatch.setattr(gr, "get_http_client", lambda: fake)

    result = await geonames_lookup("Запорожье")

    assert result["ambiguous"] is False
    assert result["name_matched"] is True
    assert len(result["candidates"]) == 1


@pytest.mark.asyncio
async def test_search_city_warns_and_lists_options(monkeypatch):
    from backend.mcp.tools import geo as geo_tools

    fake = _FakeClient({"geonames": [BARCELONA_ES, BARCELONA_VE]})
    monkeypatch.setattr(gr, "GEONAMES_USER", "test-user")
    monkeypatch.setattr(gr, "get_http_client", lambda: fake)
    monkeypatch.setattr(geo_tools, "_geocoder", None)  # rebuild with fresh state

    out = await geo_tools.search_city("Barcelona")

    assert out["resolved"] is True
    assert out["ambiguous"] is True
    assert "warning" in out, "ambiguity must never be silent"
    assert "Venezuela" in out["warning"] and "Spain" in out["warning"]
    assert len(out["candidates"]) == 2


@pytest.mark.asyncio
async def test_validate_birth_data_reports_ambiguity_as_warning_not_failure(monkeypatch):
    """A chart must not be blocked — but the caller must be told to ask."""
    from backend.mcp.tools import geo as geo_tools

    fake = _FakeClient({"geonames": [BARCELONA_ES, BARCELONA_VE]})
    monkeypatch.setattr(gr, "GEONAMES_USER", "test-user")
    monkeypatch.setattr(gr, "get_http_client", lambda: fake)
    monkeypatch.setattr(geo_tools, "_geocoder", None)

    out = await geo_tools.validate_birth_data("1977-07-01", "Barcelona", "22:30")

    assert out["valid"] is True
    assert out["issues"] == []
    assert len(out["warnings"]) == 1
    assert "Barcelona" in out["warnings"][0]


# ── caller-supplied coordinates ─────────────────────────────────────────────

def test_coordinates_must_come_as_a_pair():
    with pytest.raises(ValueError):
        NatalChartRequest(
            birth_date=date_cls(1977, 7, 1), birth_place="Zaporizhzhia", latitude=47.85
        )
    with pytest.raises(ValueError):
        NatalChartRequest(
            birth_date=date_cls(1977, 7, 1), birth_place="Zaporizhzhia", longitude=35.11
        )


def test_coordinates_are_range_checked():
    with pytest.raises(ValueError):
        NatalChartRequest(
            birth_date=date_cls(1977, 7, 1), birth_place="X",
            latitude=91.0, longitude=0.0,
        )
    with pytest.raises(ValueError):
        NatalChartRequest(
            birth_date=date_cls(1977, 7, 1), birth_place="X",
            latitude=0.0, longitude=181.0,
        )


def test_name_only_request_still_valid():
    """The existing contract must keep working unchanged."""
    req = NatalChartRequest(birth_date=date_cls(1977, 7, 1), birth_place="Запорожье")
    assert req.latitude is None and req.longitude is None


def test_timezone_is_optional_and_not_required_from_caller():
    req = NatalChartRequest(
        birth_date=date_cls(1977, 7, 1), birth_place="Zaporizhzhia",
        latitude=47.85167, longitude=35.11714,
    )
    assert req.timezone_name is None, "zone should be derivable, not mandatory"


@pytest.mark.asyncio
async def test_supplied_coordinates_skip_the_geocoder_entirely():
    """A geocoder that raises on any call proves it was never consulted."""
    from backend.services.astrology.service import AstrologyService
    from backend.services.astrology.geocoder import Geocoder

    class _ExplodingGeocoder(Geocoder):
        async def geocode(self, query):  # pragma: no cover - must not run
            raise AssertionError("geocoder must not be called when lat/lon are given")

    svc = AstrologyService(geocoder=_ExplodingGeocoder())
    req = NatalChartRequest(
        birth_date=date_cls(1977, 7, 1),
        birth_time=None,
        birth_place="Zaporizhzhia",
        latitude=47.85167,
        longitude=35.11714,
    )
    resp = await svc.calculate_natal_chart(req)

    assert float(resp.latitude) == pytest.approx(47.85167)
    assert float(resp.longitude) == pytest.approx(35.11714)
    # Zone resolved from the coordinates via tzdata, not supplied by the caller.
    assert resp.timezone == "Europe/Kyiv"


@pytest.mark.asyncio
async def test_explicit_timezone_overrides_coordinate_lookup():
    from backend.services.astrology.service import AstrologyService

    svc = AstrologyService()
    req = NatalChartRequest(
        birth_date=date_cls(1977, 7, 1),
        birth_place="somewhere",
        latitude=47.85167,
        longitude=35.11714,
        timezone_name="UTC",
    )
    resp = await svc.calculate_natal_chart(req)
    assert resp.timezone == "UTC"
