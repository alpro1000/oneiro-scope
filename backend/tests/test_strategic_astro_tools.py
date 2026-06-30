"""Smoke tests for the new astronomy MCP tools.

These exercise pure chart geometry (no LLM, no network). The fixture
chart is 1977-07-01 22:30 Zaporizhia (Europe/Kyiv) — a real chart used
for end-to-end validation throughout the session.
"""

from __future__ import annotations

import pytest

# Standard fixture: birth data for the chart we've been validating against.
NATAL = {
    "birth_date": "1977-07-01",
    "birth_time": "22:30:00",
    "birth_timezone": "Europe/Kyiv",
}


# ---------- Transits --------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_transits_returns_layer_astronomy():
    from backend.mcp.tools.strategic_astro import compute_transits

    result = await compute_transits(
        **NATAL,
        start="2026-08-01",
        end="2026-09-30",
        orb_deg=2.0,
    )
    assert result["layer"] == "astronomy"
    assert "methodology" in result
    assert "Swiss Ephemeris" in result["methodology"]


@pytest.mark.asyncio
async def test_compute_transits_finds_known_jupiter_saturn_window():
    """Jupiter conjunction natal Saturn (Leo 15°) happens around
    early-mid September 2026 — the well-known 12-year structural
    expansion marker. The transit finder must surface it."""
    from backend.mcp.tools.strategic_astro import compute_transits

    result = await compute_transits(
        **NATAL,
        start="2026-09-01",
        end="2026-09-30",
        orb_deg=2.0,
    )
    transits = result["transits"]
    jup_sat = [
        t for t in transits
        if t["transiting"] == "Jupiter"
        and t["natal"] == "Saturn"
        and t["aspect"] == "conjunction"
    ]
    assert jup_sat, f"Jupiter ☌ natal Saturn missing in Sep 2026: {transits}"
    # Should be in the first half of September.
    assert any(t["exact_date"] <= "2026-09-15" for t in jup_sat), (
        f"Expected exact date in first half of Sept, got: {jup_sat}"
    )


@pytest.mark.asyncio
async def test_compute_transits_sorted_by_date():
    from backend.mcp.tools.strategic_astro import compute_transits

    result = await compute_transits(
        **NATAL,
        start="2026-07-01",
        end="2027-06-30",
        orb_deg=2.0,
    )
    transits = result["transits"]
    dates = [t["exact_date"] for t in transits]
    assert dates == sorted(dates)


# ---------- Astrocartography ------------------------------------------------


@pytest.mark.asyncio
async def test_astrocartography_scan_returns_results_sorted_by_score():
    from backend.mcp.tools.strategic_astro import astrocartography_scan

    cities = [
        {"name": "Praha", "lat": 50.0755, "lon": 14.4378},
        {"name": "Madrid", "lat": 40.4168, "lon": -3.7038},
        {"name": "Lisboa", "lat": 38.7223, "lon": -9.1393},
        {"name": "Larnaca", "lat": 34.916, "lon": 33.624},
    ]
    result = await astrocartography_scan(**NATAL, cities=cities, orb_deg=7.0)
    assert result["layer"] == "astronomy"
    assert result["city_count"] == 4
    scores = [r["score"] for r in result["results"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_astrocartography_scan_returns_angle_hit_structure():
    """For a single city, the result must include at least one angle
    hit (with the orb of 7° wide enough to catch SOMETHING on the
    known chart), and each hit has the required fields."""
    from backend.mcp.tools.strategic_astro import astrocartography_scan

    cities = [{"name": "Larnaca", "lat": 34.916, "lon": 33.624}]
    result = await astrocartography_scan(**NATAL, cities=cities, orb_deg=7.0)
    larnaca = result["results"][0]
    assert larnaca["angle_hits"], "Wide-orb scan should find SOMETHING"
    for hit in larnaca["angle_hits"]:
        assert hit["angle"] in ("Asc", "MC", "IC", "Desc")
        assert hit["planet"] in (
            "Sun", "Moon", "Mercury", "Venus", "Mars",
            "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
        )
        assert 0 <= hit["orb_deg"] <= 7


@pytest.mark.asyncio
async def test_astrocartography_includes_all_four_angles_in_output():
    from backend.mcp.tools.strategic_astro import astrocartography_scan

    cities = [{"name": "Praha", "lat": 50.0755, "lon": 14.4378}]
    result = await astrocartography_scan(**NATAL, cities=cities)
    r = result["results"][0]
    assert all(k in r for k in ("asc", "mc", "ic", "desc"))


# ---------- Astrocartography lines + point ----------------------------------


@pytest.mark.asyncio
async def test_acg_lines_returns_geojson_with_all_angles():
    from backend.mcp.tools.strategic_astro import astrocartography_lines

    result = await astrocartography_lines(
        **NATAL, birth_lat=47.8388, birth_lon=35.1396, birth_name="Zaporizhzhia"
    )
    assert result["layer"] == "astronomy"
    fc = result["lines"]
    assert fc["type"] == "FeatureCollection"
    assert fc["features"], "should produce line features"
    angles = {f["properties"]["angle"] for f in fc["features"]}
    assert angles == {"MC", "IC", "Asc", "Desc"}
    # Every geometry is a LineString with [lon, lat] pairs in range.
    for f in fc["features"]:
        assert f["geometry"]["type"] == "LineString"
        for lon, lat in f["geometry"]["coordinates"]:
            assert -180.0 <= lon <= 180.0
            assert -90.0 <= lat <= 90.0


@pytest.mark.asyncio
async def test_acg_lines_chart_payload_is_self_contained():
    from backend.mcp.tools.strategic_astro import astrocartography_lines

    result = await astrocartography_lines(
        **NATAL, birth_lat=47.8388, birth_lon=35.1396
    )
    chart = result["chart"]
    assert 0.0 <= chart["gmst"] < 360.0
    assert 20.0 < chart["obliquity"] < 24.0
    for body in ("Sun", "Moon", "Venus", "Mars", "Saturn", "Pluto"):
        p = chart["planets"][body]
        assert {"ecl_lon", "ra", "dec"} <= set(p)
    assert chart["birth"]["lat"] == pytest.approx(47.8388, abs=1e-3)


@pytest.mark.asyncio
async def test_acg_point_brno_has_moon_on_asc():
    """Known fact for this chart: in Brno the Moon sits on the Ascendant
    (validated earlier this session). The point tool must surface it."""
    from backend.mcp.tools.strategic_astro import astrocartography_point

    result = await astrocartography_point(
        **NATAL, lat=49.195, lon=16.606, locale="en"
    )
    assert set(result["angles"]) == {"asc", "mc", "ic", "desc"}
    moon_asc = [
        c for c in result["contacts"]
        if c["planet"] == "Moon" and c["angle"] == "Asc"
    ]
    assert moon_asc, f"Moon on Asc missing for Brno: {result['contacts']}"
    assert moon_asc[0]["orb_deg"] < 1.0


@pytest.mark.asyncio
async def test_acg_point_summary_has_plain_text_both_locales():
    from backend.mcp.tools.strategic_astro import astrocartography_point

    for loc in ("ru", "en"):
        result = await astrocartography_point(
            **NATAL, lat=49.7384, lon=13.3736, locale=loc  # Plzeň
        )
        summary = result["summary"]
        assert summary["plain"], "plain-language verdict required"
        assert summary["confidence"] == 0.8
        # Plzeň has Mars tight on IC → tension bucket should be populated.
        assert summary["tension"], f"expected Mars-IC tension at Plzeň ({loc})"


def test_acg_api_rejects_invalid_timezone():
    """The HTTP layer must surface a bad timezone (→ ValueError → 400), not
    silently fall back to UTC, which would shift every angle by whole hours."""
    import datetime as _dt

    from backend.api.v1.astrology import AstrocartographyBirth, _natal_jd

    bad = AstrocartographyBirth(
        birth_date=_dt.date(1977, 7, 1),
        birth_time=_dt.time(22, 30),
        birth_timezone="Not/AZone",
    )
    with pytest.raises(ValueError):
        _natal_jd(bad)

    ok = AstrocartographyBirth(
        birth_date=_dt.date(1977, 7, 1),
        birth_time=_dt.time(22, 30),
        birth_timezone="Europe/Kyiv",
    )
    assert _natal_jd(ok) > 2_440_000  # a plausible modern Julian Day


# ---------- Solar Return ----------------------------------------------------


@pytest.mark.asyncio
async def test_solar_return_chart_returns_arcmin_accuracy():
    from backend.mcp.tools.strategic_astro import solar_return_chart

    result = await solar_return_chart(
        **NATAL,
        return_year=2026,
        location_lat=43.4452,
        location_lon=16.6890,  # Omiš
    )
    assert result["layer"] == "astronomy"
    assert result["accuracy_arcmin"] < 5.0  # tight match


@pytest.mark.asyncio
async def test_solar_return_chart_has_all_angles_and_planets():
    from backend.mcp.tools.strategic_astro import solar_return_chart

    result = await solar_return_chart(
        **NATAL,
        return_year=2026,
        location_lat=43.4452,
        location_lon=16.6890,
    )
    assert set(result["angles"]) == {"asc", "mc", "ic", "desc"}
    for body in ("Sun", "Moon", "Venus", "Mars", "Saturn", "Pluto"):
        assert body in result["planets"]
        assert body in result["planet_houses"]
        assert 1 <= result["planet_houses"][body] <= 12


@pytest.mark.asyncio
async def test_solar_return_omis_puts_sun_in_8th_house():
    """Known fact about this chart: 2026 SR in Omiš places Sun in the
    8th house (computed earlier in our session). Test locks it."""
    from backend.mcp.tools.strategic_astro import solar_return_chart

    result = await solar_return_chart(
        **NATAL,
        return_year=2026,
        location_lat=43.4452,
        location_lon=16.6890,
    )
    assert result["planet_houses"]["Sun"] == 8


@pytest.mark.asyncio
async def test_solar_return_chart_shifts_with_location():
    """Same year, different cities → different angles."""
    from backend.mcp.tools.strategic_astro import solar_return_chart

    omis = await solar_return_chart(
        **NATAL, return_year=2026,
        location_lat=43.4452, location_lon=16.6890,
    )
    klatovy = await solar_return_chart(
        **NATAL, return_year=2026,
        location_lat=49.3958, location_lon=13.2950,
    )
    # Angles must differ noticeably.
    assert abs(omis["angles"]["asc"] - klatovy["angles"]["asc"]) > 1.0
