"""WP-12/15/16/18 acceptance: contracts, scopes, illumination, small fixes.

- WP-12: the `lookup` dispatcher's documented topics match its dispatch
  table exactly, and every topic honours one response contract.
- WP-15: RFC 9728 metadata always publishes `scopes_supported`.
- WP-16: lunar illumination comes from swe_pheno_ut (77.85% on the
  audit's instant, not the flat-formula 74.08%).
- WP-18: quincunx in the aspect KB; six new dream symbols incl. mentor;
  retro list identical between horoscope and forecast paths; orb policy
  travels with the natal chart; solar return moment to the second.
"""

from __future__ import annotations

import asyncio
import re
from datetime import date, time

import pytest

from backend.mcp.tools.lookup import _TOPICS, lookup

# ── WP-12: lookup contract ──────────────────────────────────────────────────

_SAMPLE_ARGS = {
    "zodiac_sign": {"sign": "leo"},
    "sun_in_sign": {"sign": "leo"},
    "mc_in_sign": {"sign": "scorpio"},
    "house_meaning": {"house_number": 2},
    "planet_in_house": {"planet": "mars", "house_number": 3},
    "planet_dignity": {"planet": "venus", "sign": "taurus"},
    "aspect_meaning": {"aspect": "square"},
    "transit_meaning": {"transiting": "saturn", "aspect": "square", "natal": "sun"},
}


def test_docstring_topics_match_dispatch_table():
    """WP-12: the documented contract and the code must be the same list."""
    documented = set(re.findall(r'- "([a-z_]+)"', lookup.__doc__))
    assert documented == set(_TOPICS), (
        f"doc-only: {sorted(documented - set(_TOPICS))}; "
        f"undocumented: {sorted(set(_TOPICS) - documented)}"
    )


@pytest.mark.parametrize("topic", sorted(_TOPICS))
def test_every_topic_returns_the_contract_shape(topic):
    out = lookup(topic, **_SAMPLE_ARGS.get(topic, {}))
    assert isinstance(out, dict)
    assert "error" not in out, f"{topic}: {out.get('error')}"
    assert out.get("topic") == topic
    # A topic either carries a payload dict of its own or a bare items list
    # wrapped under "items" — never a naked list (the WP-12 complaint).
    if "items" in out:
        assert isinstance(out["items"], (list, dict))


def test_unknown_topic_lists_the_valid_ones():
    out = lookup("no_such_topic")
    assert "error" in out and out["topics"] == sorted(_TOPICS)


def test_missing_required_args_are_named():
    out = lookup("planet_in_house")
    assert "error" in out and set(out["missing"]) == {"planet", "house_number"}


# ── WP-15: scopes_supported always published ────────────────────────────────

def test_scopes_supported_published_without_required_scopes(monkeypatch):
    from backend.core.config import settings
    from backend.mcp import remote

    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", "https://idp.example.com/")
    monkeypatch.setattr(settings, "MCP_REQUIRED_SCOPES", "")
    meta = remote.protected_resource_metadata()
    assert meta["scopes_supported"] == ["openid", "profile", "email"]


def test_required_scopes_still_win(monkeypatch):
    from backend.core.config import settings
    from backend.mcp import remote

    monkeypatch.setattr(settings, "MCP_AUTH_ISSUER", "https://idp.example.com/")
    monkeypatch.setattr(settings, "MCP_REQUIRED_SCOPES", "mcp:read")
    meta = remote.protected_resource_metadata()
    assert meta["scopes_supported"] == ["mcp:read"]


# ── WP-16: illumination via swe_pheno_ut ────────────────────────────────────

def test_illumination_matches_pheno_on_the_audit_instant():
    """2026-08-03 10:00 UTC must give ~77.85%, not the flat-formula 74.08%.

    Noon in Europe/Kaliningrad (UTC+2, no DST) IS 10:00 UTC — the exact
    instant from the audit.
    """
    from backend.services.lunar.engine import compute_lunar

    result = compute_lunar("2026-08-03", "Europe/Kaliningrad")
    assert result.illumination == pytest.approx(0.77850, abs=0.002)
    assert result.provenance["illumination_method"] == "swe_pheno_ut"


# ── WP-18: quincunx, symbols, retro sync, orb policy, solar seconds ─────────

def test_quincunx_has_a_kb_meaning():
    out = lookup("aspect_meaning", aspect="quincunx")
    assert out["angle_deg"] == 150
    assert "quincunx" not in out.get("error", "")
    assert out["archetype"]


def test_new_symbols_are_in_the_dictionary():
    items = lookup("dream_symbols")["items"]
    ids = {s["symbol"] if isinstance(s, dict) else s for s in items}
    expected = {"gold", "treasure", "earth_soil", "hiding_place", "pockets", "mentor"}
    missing = expected - ids
    assert not missing, f"symbols missing: {sorted(missing)}"


def test_mentor_and_treasure_detected_in_the_coin_dream():
    from backend.services.dreams.analyzer import DreamAnalyzer

    analyzer = DreamAnalyzer()
    result = analyzer.analyze(
        "Наставник говорит, где нужно копать землю, и я нахожу клад — "
        "золотые монеты кладу в карманы."
    )
    symbols = result[0]
    found = {s.symbol if hasattr(s, "symbol") else s["symbol"] for s in symbols}
    assert {"mentor", "treasure"} <= found


def test_mentor_is_a_male_character_in_hvdc():
    from backend.services.dreams.hvdc_coder import HvdcCoder

    coding = HvdcCoder().code("Наставник показал мне дорогу.")
    assert [(c.noun, c.gender) for c in coding.characters] == [("наставник", "male")]


def test_horoscope_retro_list_matches_forecast_source():
    """WP-18: the horoscope used to compute retrogrades only when a natal
    chart was supplied — the same date disagreed between the two tools."""
    from backend.services.astrology import AstrologyService
    from backend.services.astrology.schemas import HoroscopePeriod, HoroscopeRequest

    service = AstrologyService()
    target = date(2026, 8, 3)
    resp = asyncio.run(
        service.generate_horoscope(
            HoroscopeRequest(period=HoroscopePeriod.DAILY, target_date=target,
                             locale="ru")
        )
    )
    expected = service.transit_calculator.get_retrograde_planets(target)
    assert resp.retrograde_planets == expected
    assert expected, "2026-08-03 has retrograde planets — empty means the bug"


def test_natal_chart_carries_the_orb_policy():
    from backend.services.astrology import AstrologyService, NatalChartRequest

    resp = asyncio.run(AstrologyService().calculate_natal_chart(
        NatalChartRequest(
            birth_date=date(1977, 7, 1), birth_time=time(22, 30),
            birth_place="Zaporizhzhia", latitude=47.8388, longitude=35.1396,
            locale="ru",
        ),
        interpret=False,
    ))
    policy = resp.orb_policy_deg
    assert policy["conjunction"] == 10.0
    assert policy["quincunx"] == 3.0
    assert set(policy) == {
        "conjunction", "opposition", "trine", "square", "sextile", "quincunx"
    }
    # Every emitted aspect respects the policy it declares.
    for aspect in resp.aspects:
        assert aspect.orb_deg <= policy[aspect.aspect_type.value] + 1e-9


def test_solar_return_moment_is_reported_to_the_second():
    import swisseph as swe

    from backend.services.astrology.solar_return import solar_return

    natal_jd = swe.julday(1977, 7, 1, 19.5)
    sr = solar_return(natal_jd, 2026, 47.8388, 35.1396)
    # ISO with seconds, and the refinement pinned the Sun to sub-arcsecond
    # territory (the Sun moves ~0.04 arcsec per second of time).
    assert re.search(r"T\d{2}:\d{2}:\d{2}\+00:00$", sr.exact_moment_utc)
    assert sr.accuracy_arcmin < 0.01
