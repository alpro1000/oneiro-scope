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


# ---------- Historic timezone resolution ------------------------------------


def test_resolve_birth_moment_soviet_decree_time():
    """USSR 1977: Zaporizhzhia ran on Moscow decree time — UTC+3, no DST
    yet. The resolver must reproduce the offset we validated by hand."""
    import datetime as _dt

    from backend.services.astrology.historic_tz import resolve_birth_moment

    m = resolve_birth_moment(
        _dt.date(1977, 7, 1), _dt.time(22, 30),
        lat=47.8388, lon=35.1396,
    )
    assert m.utc_offset_hours == 3.0
    assert m.source == "coordinates"
    assert not m.pre_1970


def test_resolve_birth_moment_explicit_tz_and_winter():
    """January 1989 Ukraine: still UTC+3 (Moscow time, winter)."""
    import datetime as _dt

    from backend.services.astrology.historic_tz import resolve_birth_moment

    m = resolve_birth_moment(
        _dt.date(1989, 1, 24), _dt.time(22, 30),
        timezone_name="Europe/Kyiv",
    )
    assert m.utc_offset_hours == 3.0
    assert m.source == "explicit"


def test_resolve_birth_moment_rejects_bad_tz():
    import datetime as _dt

    from backend.services.astrology.historic_tz import resolve_birth_moment

    with pytest.raises(ValueError):
        resolve_birth_moment(
            _dt.date(2000, 1, 1), _dt.time(12, 0),
            timezone_name="Not/AZone",
        )


# ---------- Clean-luck flag + compare + themes -------------------------------


@pytest.mark.asyncio
async def test_relocation_summary_clean_flag_warsaw_vs_prague():
    """Session-validated: Warsaw = Venus-IC with no malefic (clean);
    Prague = Venus-IC far + Mars-IC 0.3° (mixed)."""
    from backend.mcp.tools.strategic_astro import astrocartography_point

    warsaw = await astrocartography_point(**NATAL, lat=52.23, lon=21.01)
    prague = await astrocartography_point(**NATAL, lat=50.0755, lon=14.4378)
    assert warsaw["summary"]["clean"] is True
    assert prague["summary"]["clean"] is False


@pytest.mark.asyncio
async def test_compare_relocations_preserves_order():
    from backend.mcp.tools.strategic_astro import compare_relocations

    result = await compare_relocations(
        **NATAL,
        locations=[
            {"name": "Zaporizhzhia", "lat": 47.8388, "lon": 35.1396},
            {"name": "Brno", "lat": 49.195, "lon": 16.606},
        ],
    )
    names = [l["name"] for l in result["locations"]]
    assert names == ["Zaporizhzhia", "Brno"]
    for loc in result["locations"]:
        assert "clean" in loc["summary"]
        assert set(loc["angles"]) == {"asc", "mc", "ic", "desc"}


@pytest.mark.asyncio
async def test_theme_scan_luck_flags_warsaw_clean():
    from backend.mcp.tools.strategic_astro import scan_cities_by_theme

    result = await scan_cities_by_theme(
        **NATAL,
        theme="luck",
        cities=[
            {"name": "Warsaw", "lat": 52.23, "lon": 21.01},
            {"name": "Prague", "lat": 50.0755, "lon": 14.4378},
        ],
    )
    rows = {r["name"]: r for r in result["results"]}
    assert rows["Warsaw"]["clean"] is True
    assert rows["Prague"]["clean"] is False
    # Ranking must put clean Warsaw above Mars-dominated Prague.
    assert result["results"][0]["name"] == "Warsaw"


@pytest.mark.asyncio
async def test_theme_scan_rejects_unknown_theme():
    from backend.mcp.tools.strategic_astro import scan_cities_by_theme

    with pytest.raises(ValueError):
        await scan_cities_by_theme(
            **NATAL, theme="wealth",
            cities=[{"name": "X", "lat": 0.0, "lon": 0.0}],
        )


# ---------- Thematic transit arcs --------------------------------------------

# Chart validated in session: 1989-01-24 22:30 Zaporizhzhia (Mars+Jupiter
# in the 8th, Pluto in the 2nd) — the debt-theme fixture.
NATAL_1989 = {
    "birth_date": "1989-01-24",
    "birth_time": "22:30:00",
    "birth_timezone": "Europe/Kyiv",
}


@pytest.mark.asyncio
async def test_transit_arc_money_debt_finds_pluto_mars_pressure():
    """Hand-validated: Pluto □ natal Mars (8th house) peaks January and
    October 2026. The arc must surface both as pressure events."""
    from backend.mcp.tools.strategic_astro import transit_arc

    result = await transit_arc(
        **NATAL_1989,
        birth_lat=47.8388, birth_lon=35.1396,
        theme="money_debt",
        start="2026-01-01", end="2026-12-31",
    )
    assert "Mars" in result["significators"]
    assert "Jupiter" in result["significators"]
    pluto_mars = [
        e for e in result["events"]
        if e["transiting"] == "Pluto" and e["natal"] == "Mars"
        and e["aspect"] == "square"
    ]
    assert len(pluto_mars) >= 2, result["events"]
    assert result["phases"], "events must be grouped into phases"
    kinds = {p["kind"] for p in result["phases"]}
    assert kinds <= {"pressure", "support"}


@pytest.mark.asyncio
async def test_transit_arc_rejects_unknown_theme():
    from backend.mcp.tools.strategic_astro import transit_arc

    with pytest.raises(ValueError):
        await transit_arc(
            **NATAL_1989, birth_lat=47.8, birth_lon=35.1,
            theme="fortune", start="2026-01-01", end="2026-02-01",
        )


# ---------- Synastry ----------------------------------------------------------


@pytest.mark.asyncio
async def test_synastry_returns_aspects_and_bounded_scores():
    from backend.mcp.tools.strategic_astro import synastry

    result = await synastry(
        person_a=NATAL,
        person_b={
            "birth_date": "1978-03-26",
            "birth_time": "03:20:00",
            "birth_timezone": "Europe/Kyiv",
        },
    )
    assert result["aspect_count"] == len(result["aspects"]) > 0
    for a in result["aspects"]:
        assert a["nature"] in ("harmonious", "tense", "intense")
        assert 0 <= a["orb_deg"] <= 7.0
    dims = result["summary"]["dimensions"]
    assert set(dims) == {
        "attraction", "emotional", "communication", "stability", "tension"
    }
    for v in dims.values():
        assert 0.0 <= v <= 100.0
    assert 0.0 <= result["summary"]["overall_score"] <= 100.0
    assert result["summary"]["plain"]


@pytest.mark.asyncio
async def test_synastry_is_symmetric_in_aspect_count():
    """Swapping persons must yield the same number of inter-aspects."""
    from backend.mcp.tools.strategic_astro import synastry

    b = {
        "birth_date": "1989-01-24",
        "birth_time": "22:30:00",
        "birth_timezone": "Europe/Kyiv",
    }
    ab = await synastry(person_a=NATAL, person_b=b)
    ba = await synastry(person_a=b, person_b=NATAL)
    assert ab["aspect_count"] == ba["aspect_count"]


# ---------- Solar Return suggestions ------------------------------------------


@pytest.mark.asyncio
async def test_solar_return_suggest_ranks_candidates():
    from backend.mcp.tools.strategic_astro import solar_return_suggest

    result = await solar_return_suggest(
        **NATAL,
        return_year=2026,
        candidates=[
            {"name": "Omiš", "lat": 43.4452, "lon": 16.6890},
            {"name": "Klatovy", "lat": 49.3958, "lon": 13.2950},
        ],
    )
    ranking = result["ranking"]
    assert len(ranking) == 2
    scores = [r["score"] for r in ranking]
    assert scores == sorted(scores, reverse=True)
    for r in ranking:
        for ap in r["angular_planets"]:
            assert ap["house"] in (1, 4, 7, 10)


# ---------- Report builder ------------------------------------------------------


def test_build_report_structure_and_html():
    import datetime as _dt

    from backend.services.astrology.historic_tz import resolve_birth_moment
    from backend.services.astrology.report import build_report, render_html

    moment = resolve_birth_moment(
        _dt.date(1977, 7, 1), _dt.time(22, 30),
        lat=47.8388, lon=35.1396,
    )
    report = build_report(
        moment,
        birth_place=("Zaporizhzhia", 47.8388, 35.1396),
        current_place=("Plzeň", 49.7384, 13.3736),
        year_start=_dt.date(2026, 7, 1),
        cities=[("Warsaw", 52.23, 21.01), ("Prague", 50.0755, 14.4378)],
    )
    assert set(report) >= {
        "birth", "natal", "relocations", "themes", "year_transits",
        "provenance", "disclaimer",
    }
    assert report["birth"]["utc_offset_hours"] == 3.0
    assert len(report["relocations"]) == 2
    assert set(report["themes"]) == {"luck", "career", "relationships", "home"}
    # Known natal anchor: Sun ~9°49' Cancer.
    assert "Рак" in report["natal"]["Sun"]["position"]

    html = render_html(report)
    assert html.startswith("<!DOCTYPE html>")
    assert "Warsaw" in html or "Варшава" in html
    assert report["disclaimer"][:30] in html
