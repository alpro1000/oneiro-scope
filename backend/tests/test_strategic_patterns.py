"""Tests for the analysis-pattern engine + MCP tool wrappers.

Pure ephemeris (Moshier) + KB lookups — no network, no LLM, no PII.
Test chart is a neutral fixture: 1990-05-15 14:30 Europe/Moscow.
"""

from __future__ import annotations

import re

import pytest

from backend.services.strategic.pattern_engine import (
    SIGNS,
    SIGN_RULERS,
    decade_map,
    electional_day,
    life_pivots,
    money_contour,
    natal_geometry,
    reverse_physiognomy,
    vocation_map,
)

BIRTH = dict(
    birth_date="1990-05-15",
    birth_time="14:30",
    birth_timezone="Europe/Moscow",
    lat=55.7558,
    lon=37.6173,
)


@pytest.fixture(scope="module")
def geo():
    return natal_geometry(**BIRTH)


# --- natal geometry -----------------------------------------------------------

def test_natal_geometry_basics(geo):
    assert geo["planets"]["sun"]["sign"] == "taurus"  # May 15 → Taurus
    assert set(geo["cusps"]) == set(range(1, 13))
    for p in geo["planets"].values():
        assert 1 <= p["house"] <= 12
        assert p["sign"] in SIGNS
    assert geo["provenance"]["ephemeris_engine"] == "SwissEph/MOSEPH"


def test_legacy_timezone_alias():
    """Deprecated IANA names (merged in tzdata 2022b) must still resolve."""
    legacy = natal_geometry("1985-03-10", "08:00", "Europe/Zaporozhye",
                            47.8388, 35.1396)
    canonical = natal_geometry("1985-03-10", "08:00", "Europe/Kyiv",
                               47.8388, 35.1396)
    assert legacy["utc"] == canonical["utc"]
    with pytest.raises(Exception, match="canonical IANA name"):
        natal_geometry("1985-03-10", "08:00", "Mars/Olympus", 0.0, 0.0)


def test_sect_and_part_of_fortune_formula(geo):
    # 14:30 local in May in Moscow — Sun above horizon → day chart.
    assert geo["sect"] == "day"
    asc = geo["angles"]["asc"]
    s, m = geo["planets"]["sun"]["lon"], geo["planets"]["moon"]["lon"]
    expected = (asc + m - s) % 360.0
    assert abs(expected - geo["part_of_fortune"]["lon"]) < 0.05


# --- money-contour ------------------------------------------------------------

def test_money_contour_structure(geo):
    mc = money_contour(geo)
    for block in ("house_2", "house_8", "house_11"):
        b = mc[block]
        assert b["cusp_sign"] in SIGNS
        assert b["rulers"] and all(
            r["planet"] in SIGN_RULERS[b["cusp_sign"]] for r in b["rulers"]
        )
    lp = mc["linchpin"]
    assert isinstance(lp["linked"], bool)
    assert lp["type"] in ("same_ruler", "conjunction_of_rulers")
    pof = mc["part_of_fortune"]
    assert pof["sign"] in SIGNS and 1 <= pof["house"] <= 12


# --- vocation-map ---------------------------------------------------------------

def test_vocation_map_structure(geo):
    vm = vocation_map(geo)
    assert vm["mc"]["sign"] in SIGNS
    assert vm["mc"]["rulers"]
    for entry in vm["angular"]:
        assert entry["house"] in (1, 4, 7, 10)
    for entry in vm["dignified"]:
        assert entry["status"] in ("domicile", "exaltation")
    assert set(vm["work_houses"]) == {"2", "6", "10"}


# --- decade-map -----------------------------------------------------------------

def test_decade_map_two_years(geo):
    dm = decade_map(geo, start_year=2026, years=2)
    assert [y["year"] for y in dm["years"]] == [2026, 2027]
    y2026 = dm["years"][0]["placements_jul1"]
    assert y2026["pluto"]["sign"] == "aquarius"  # mid-2026 Pluto in Aquarius
    for y in dm["years"]:
        for hit in y["hits"]:
            assert re.fullmatch(r"\d{4}-\d{2}", hit["date"])
            assert hit["aspect"] in (
                "conjunction", "sextile", "square", "trine", "opposition"
            )


def test_decade_map_caps_years(geo):
    dm = decade_map(geo, start_year=2026, years=99)
    assert len(dm["years"]) == 12


# --- life-pivots ----------------------------------------------------------------

def test_life_pivots_structure(geo):
    lp = life_pivots(geo, from_year=2018, to_year=2024)
    for w in lp["windows"]:
        assert re.fullmatch(r"\d{4}-\d{2}", w["date"])
        assert w["transiting"] in ("saturn", "uranus", "neptune", "pluto")
        assert w["point"] in ("asc", "mc", "ic", "dsc", "sun", "moon")
        assert w["relocation_marker"] in (None, "strong", "possible")
    assert len(lp["validation_questions"]) == len(lp["windows"])


def test_life_pivots_catches_fast_saturn_return(geo):
    """Regression: the 10-day grid must not leap over fast-Saturn passes.

    1990 fixture: natal Saturn ~25° Capricorn → first Saturn return falls
    in 2019-2020. A monthly grid can miss ±1° windows entirely (Saturn
    moves up to ~3.7°/month near its solar conjunction).
    """
    lp = life_pivots(geo, from_year=2018, to_year=2021)
    returns = [c for c in lp["cycles"] if c["cycle"] == "saturn_return"]
    assert returns, "first Saturn return must be detected in 2018-2021"
    assert all(28 <= c["age"] <= 31 for c in returns)


def test_life_pivots_allows_single_year(geo):
    """Both bounds are documented inclusive — a one-year scan must work."""
    lp = life_pivots(geo, from_year=2020, to_year=2020)
    assert all(w["date"].startswith("2020-") for w in lp["windows"])


def test_life_pivots_rejects_bad_window(geo):
    with pytest.raises(ValueError):
        life_pivots(geo, from_year=2020, to_year=2018)
    with pytest.raises(ValueError):
        life_pivots(geo, from_year=1900, to_year=2000)


# --- electional-day -------------------------------------------------------------

def test_electional_day_known_date(geo):
    ed = electional_day(geo, "2026-07-22", "UTC")
    assert ed["moon_sign_at_start"] == "scorpio"
    assert ed["phase"]["waxing"] is True  # elongation ~100° that day
    assert ed["mercury_retrograde"] is True  # direct ~Jul 24, 2026
    assert ed["steps"], "grid must not be empty"
    for s in ed["steps"]:
        assert re.fullmatch(r"\d{2}:\d{2}", s["time"])
        assert s["moon_sign"] in SIGNS
        for h in s["natal_hits"]:
            assert h["nature"] in ("harmonious", "tense", "neutral")


# --- reverse-physiognomy --------------------------------------------------------

def test_electional_day_voc_sees_mirror_aspects(geo):
    """Regression: the VoC scan must watch 240/270/300 offsets too.

    With only 0..180 offsets the Moon's last exact aspect before ingress was
    missed, so 2026-09-02 (Europe/Prague) came back void the whole day.
    """
    ed = electional_day(geo, "2026-09-02", "Europe/Prague")
    assert ed["void_of_course"]["start_local"] == "2026-09-02 12:50"
    assert not all(s["void_of_course"] for s in ed["steps"])
    assert ed["supportive_step_times"]


@pytest.mark.parametrize(
    "kwargs",
    [{"day_end": 24}, {"day_start": 20, "day_end": 8}, {"step_min": 0}],
)
def test_electional_day_validates_grid(geo, kwargs):
    """Bad hour/step arguments raise a clear ValueError, not a raw datetime one."""
    with pytest.raises(ValueError):
        electional_day(geo, "2026-09-02", "Europe/Prague", **kwargs)


def test_reverse_physiognomy_flat_kb_entries_carry_features():
    """Regression: western.json nodes are flat {ru,en,source} — not {shape,…}.

    Reading them as nested left face_features empty, so the portrait prompt
    seed the character-face skill builds was blank.
    """
    res = reverse_physiognomy(
        ["избирательность", "вязкость"], subject_type="fictional"
    )
    assert res["matched"], "western traits must match"
    assert all(m["face_features"] for m in res["matched"])
    assert all(m["kb_reading"] for m in res["matched"])
    assert res["face_feature_seed"]


def test_reverse_physiognomy_maps_traits():
    res = reverse_physiognomy(
        ["дисциплина и порядок", "стратег", "избирательность"],
        subject_type="fictional",
    )
    systems = {(m["system"], m["type"]) for m in res["matched"]}
    assert ("mianxiang", "metal") in systems
    assert ("mianxiang", "wood") in systems
    assert ("western", "retracted") in systems
    assert res["face_feature_seed"]
    for m in res["matched"]:
        assert m["source"], "every KB match must carry its citation"


def test_reverse_physiognomy_ethics_gate():
    with pytest.raises(ValueError):
        reverse_physiognomy(["харизма"], subject_type="third_party")


def test_reverse_physiognomy_reports_unmatched():
    res = reverse_physiognomy(["квазиморфность"], subject_type="self")
    assert res["unmatched_traits"] == ["квазиморфность"]


# --- MCP tool wrappers ----------------------------------------------------------

def test_tool_wrappers_carry_provenance_and_refs():
    from backend.mcp.tools.strategic_patterns import (
        money_contour as t_money,
        reverse_physiognomy_prompt as t_face,
    )

    out = t_money(**BIRTH)
    assert out["pattern_id"] == "money-contour"
    assert out["layer"] == "astronomy" and out["confidence"] == 1.0
    assert "analysis_patterns.json#money-contour" in out["interpretation_rules_ref"]
    assert out["disclaimer"]
    assert out["computed"]["house_2"]["cusp_sign"] in SIGNS

    face = t_face(["дисциплина"], subject_type="fictional")
    assert face["confidence"] == 0.6  # physiognomy dictionary tier
    assert face["ethics_gate"] == "fictional_or_self_only"
