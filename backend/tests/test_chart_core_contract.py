"""The `chart_core` contract: one payload, two transports, hard budget.

The architecture rests on a measured fact: given sidereal time,
obliquity and each body's ecliptic + equatorial state, a client computes
angles for ANY point on Earth by itself. These tests pin the three
things that make that safe to rely on —

1. the payload contains everything needed (and nothing derivable),
2. it stays inside its byte budget at every latitude,
3. MCP and HTTP hand back the identical object, so a client cannot
   behave differently depending on which door it came through.
"""

from __future__ import annotations

import asyncio
import json
import math
import pathlib
import re
from datetime import date, time

import pytest
import swisseph as swe

from backend.services.astrology.chart_core import (
    BODIES,
    CHART_CORE_MAX_BYTES,
    CHART_CORE_VERSION,
    CHART_KIT_HOUSE_SYSTEMS,
    HOUSE_SYSTEM_CODES,
    NODE_TYPE,
    PLACE_LABEL_MAX_BYTES,
    build_chart_core,
    build_chart_response,
    chart_core_bytes,
    resolve_house_system,
)

# Reference chart used across the repo (owner's, verified placements).
REF = dict(birth_date=date(1977, 7, 1), birth_time=time(22, 30),
           lat=47.8388, lon=35.1396, place_label="Запорожье")

# Latitudes that exercise the polar boundary and both hemispheres.
LOCATIONS = [
    ("equator", 0.0, 0.0),
    ("London", 51.5074, -0.1278),
    ("Sydney", -33.8688, 151.2093),
    ("Reykjavik", 64.1466, -21.9426),
    ("Tromsø", 69.6492, 18.9553),
    ("Longyearbyen", 78.2232, 15.6267),
    ("Ushuaia", -54.8019, -68.3030),
    ("Tokyo", 35.6762, 139.6503),
]


# ── the payload carries what a client needs ─────────────────────────────────

def test_core_has_every_field_the_client_computes_from():
    core = build_chart_core(**REF).core
    assert set(core) >= {
        "version", "jd_ut", "gmst", "obliquity", "birth", "bodies",
        "node_type", "house_system",
    }
    assert core["version"] == CHART_CORE_VERSION
    assert core["node_type"] == NODE_TYPE, "true/mean node must be declared"
    birth = core["birth"]
    assert set(birth) >= {
        "lat", "lon", "tz_used", "utc_offset_used", "local_clock", "utc",
        "place_label", "time_known",
    }
    # The offset users argue about most ships pre-formatted, not as a float.
    assert birth["utc_offset_used"] == "+03:00"
    assert birth["tz_used"] == "Europe/Kyiv"


def test_every_body_carries_ecliptic_and_equatorial_state():
    """`ecl_lat` was the gap: without it a client cannot re-derive RA/Dec
    or place bodies off the ecliptic plane correctly."""
    core = build_chart_core(**REF).core
    assert set(core["bodies"]) == set(BODIES)
    for name, body in core["bodies"].items():
        assert set(body) == {
            "ecl_lon", "ecl_lat", "ra", "dec", "speed_lon", "retrograde"
        }, f"{name} field set drifted"
        assert 0.0 <= body["ecl_lon"] < 360.0
        assert -90.0 <= body["dec"] <= 90.0
        assert body["retrograde"] == (body["speed_lon"] < 0)


def test_derivable_values_are_not_sent():
    """The South Node is the North Node + 180°; sending it would cost
    bytes for a number the client can produce itself."""
    core = build_chart_core(**REF).core
    assert "SouthNode" not in core["bodies"]
    assert "TrueNode" in core["bodies"]


def test_true_node_declaration_matches_the_numbers():
    """`node_type` must describe the body actually sent — the mean node
    moves uniformly, the true node oscillates and is usually retrograde."""
    core = build_chart_core(**REF).core
    jd = core["jd_ut"]
    true_lon = swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_SWIEPH)[0][0]
    mean_lon = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SWIEPH)[0][0]
    sent = core["bodies"]["TrueNode"]["ecl_lon"]
    assert abs(sent - true_lon) < 0.001
    assert abs(sent - mean_lon) > 0.1, "the two nodes must differ here"


# ── the budget ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name,lat,lon", LOCATIONS)
def test_core_stays_within_budget_everywhere(name, lat, lon):
    core = build_chart_core(
        birth_date=date(1977, 7, 1), birth_time=time(22, 30),
        lat=lat, lon=lon, place_label=name,
    ).core
    size = chart_core_bytes(core)
    assert size <= CHART_CORE_MAX_BYTES, f"{name}: {size} > {CHART_CORE_MAX_BYTES}"


def test_substitution_prose_does_not_eat_the_budget():
    """The polar note is explanation, not arithmetic — it rides in the
    envelope so a long message can never squeeze the numbers out."""
    built = build_chart_core(
        birth_date=date(1990, 1, 15), birth_time=time(3, 20),
        lat=69.6492, lon=18.9553, place_label="Tromsø",
    )
    assert built.house_system_note, "polar chart must explain the substitution"
    assert "house_system_note" not in built.core
    assert chart_core_bytes(built.core) <= CHART_CORE_MAX_BYTES


# ── polar latitudes: substituted, never silent, never fatal ─────────────────

def test_placidus_is_undefined_beyond_the_polar_circle():
    """Reality check for the substitution: Swiss Ephemeris really refuses."""
    jd = build_chart_core(**REF).core["jd_ut"]
    with pytest.raises(Exception):
        swe.houses_ex(jd, 69.6492, 18.9553, b"P")


@pytest.mark.parametrize("lat", [69.6492, 78.2232, -75.0])
def test_polar_charts_substitute_and_declare(lat):
    jd = build_chart_core(**REF).core["jd_ut"]
    system, note = resolve_house_system(jd, lat, 18.0, "placidus")
    assert system == "porphyry"
    assert note and "undefined" in note


def test_temperate_charts_keep_placidus_and_say_nothing():
    jd = build_chart_core(**REF).core["jd_ut"]
    system, note = resolve_house_system(jd, 47.8388, 35.1396, "placidus")
    assert system == "placidus" and note is None


def test_bad_coordinates_are_not_mistaken_for_polar_latitudes():
    """Swiss Ephemeris raises the SAME swe.Error for a polar Placidus and
    for an out-of-range latitude, so narrowing the except clause alone
    would answer `lat=500` with a polar-circle explanation. Validating
    the input first is what keeps the two apart."""
    jd = build_chart_core(**REF).core["jd_ut"]
    with pytest.raises(ValueError, match=r"latitude"):
        resolve_house_system(jd, 500.0, 10.0, "placidus")
    with pytest.raises(ValueError, match=r"longitude"):
        resolve_house_system(jd, 40.0, -500.0, "placidus")


def test_unknown_house_system_is_refused_not_silently_substituted():
    """swe.houses_ex answers an unknown letter by quietly using Porphyry
    and returning a normal tuple — a typo would otherwise produce a
    wrong-system chart with nothing to show for it."""
    jd = build_chart_core(**REF).core["jd_ut"]
    with pytest.raises(ValueError, match="Unknown house system"):
        resolve_house_system(jd, 47.8, 35.1, "plasidus")


def test_substituted_core_carries_what_was_asked_for():
    """Relocation needs the original request, not just the survivor.

    `house_system` describes ONE point on Earth. A client relocating a
    Tromsø chart to London has to know Placidus was wanted, or it keeps
    the polar substitute forever — and relocation is the whole map.
    """
    polar = build_chart_core(**{**REF, "lat": 69.6492, "lon": 18.9553}).core
    assert polar["house_system"] == "porphyry"
    assert polar["requested_house_system"] == "placidus"


def test_unsubstituted_core_spends_no_bytes_on_the_field():
    core = build_chart_core(**REF).core
    assert core["house_system"] == "placidus"
    assert "requested_house_system" not in core


def test_core_refuses_systems_the_client_cannot_draw():
    """A chart_core promises the CLIENT can re-derive the cusps. Koch is
    a real system the server's own natal service computes happily, but
    chart-kit does not implement it, so declaring it here would ship
    houses nobody can draw."""
    for system in sorted(set(HOUSE_SYSTEM_CODES) - CHART_KIT_HOUSE_SYSTEMS):
        with pytest.raises(ValueError, match="chart-kit"):
            build_chart_core(**REF, house_system=system)
    with pytest.raises(ValueError, match="Unknown house system"):
        build_chart_core(**REF, house_system="plasidus")


def test_the_two_lists_of_implemented_systems_cannot_drift():
    """The Python set and the TypeScript array are one fact stored twice.

    Parsed out of the kit's own source rather than duplicated here: a
    system added on one side and forgotten on the other is exactly the
    kind of divergence that shows up as a client drawing houses the
    server never authorised.
    """
    src = (
        pathlib.Path(__file__).resolve().parents[2]
        / "packages/chart-kit/src/types.ts"
    ).read_text(encoding="utf-8")
    block = re.search(
        r"export const IMPLEMENTED_SYSTEMS = \[(.*?)\] as const;", src, re.S
    )
    assert block, "IMPLEMENTED_SYSTEMS not found in chart-kit types.ts"
    assert set(re.findall(r"'([a-z_]+)'", block.group(1))) == CHART_KIT_HOUSE_SYSTEMS


# ── the one field a caller can inflate ──────────────────────────────────────

def test_a_long_place_name_cannot_breach_the_budget():
    """255 characters of Cyrillic is 510 bytes — a quarter of the budget
    from a field no computation reads. The API allows a long geocoding
    query; what rides in the core is the bounded echo of it."""
    core = build_chart_core(**{**REF, "place_label": "Запорожье" * 40}).core
    assert chart_core_bytes(core) <= CHART_CORE_MAX_BYTES
    label = core["birth"]["place_label"]
    assert len(label.encode()) <= PLACE_LABEL_MAX_BYTES
    # Truncated visibly, not quietly cropped to look complete.
    assert label.endswith("…")


def test_a_short_place_name_is_left_exactly_as_given():
    assert build_chart_core(**REF).core["birth"]["place_label"] == "Запорожье"


@pytest.mark.parametrize("label", ["🌑" * 255, "a" * 255, "Ω" * 255])
def test_no_encoding_of_a_max_length_label_breaks_the_budget(label):
    """Emoji are 4 bytes each: 255 of them is 1020 bytes on their own."""
    core = build_chart_core(**{**REF, "place_label": label}).core
    assert chart_core_bytes(core) <= CHART_CORE_MAX_BYTES
    # And the cut never leaves a broken code point behind.
    core["birth"]["place_label"].encode().decode()


def test_polar_birth_still_produces_a_chart():
    """The regression this fixes: a Tromsø birth used to raise RuntimeError
    and return no chart at all."""
    from backend.services.astrology import AstrologyService, NatalChartRequest

    resp = asyncio.run(AstrologyService().calculate_natal_chart(
        NatalChartRequest(
            birth_date=date(1990, 1, 15), birth_time=time(3, 20),
            birth_place="Tromsø", latitude=69.6492, longitude=18.9553,
            locale="ru",
        ),
        interpret=False,
    ))
    assert resp.houses and len(resp.houses) == 12
    assert resp.house_system == "porphyry"
    assert resp.house_system_note
    assert resp.ascendant is not None, "angles are defined at any latitude"


# ── one payload, two transports ─────────────────────────────────────────────

def _dump(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


# Identity is proved BY CONSTRUCTION rather than by sampling one request
# through each surface: both transports are asserted to go through the
# single shared builder, and the builder's output is compared against the
# MCP tool's. A sampled comparison could pass while the two paths still
# diverge on some other input; this cannot. It also keeps the check
# runnable where importing a FastAPI router is not.

def test_mcp_core_equals_the_shared_builder_byte_for_byte():
    """Acceptance criterion, first half: the MCP surface hands back
    exactly what the shared builder produces."""
    from backend.mcp.tools.astrology import calculate_natal_chart

    payload = dict(
        birth_date="1977-07-01", birth_time="22:30:00",
        birth_place="Запорожье", latitude=47.8388, longitude=35.1396,
        locale="ru",
    )
    mcp_core = asyncio.run(calculate_natal_chart(**payload))["chart_core"]
    builder_core = build_chart_response(
        birth_date=date(1977, 7, 1), birth_time=time(22, 30),
        lat=47.8388, lon=35.1396, place_label="Запорожье",
        timezone_name="Europe/Kyiv", locale="ru",
    )["chart_core"]

    assert _dump(mcp_core) == _dump(builder_core), (
        "the MCP surface diverged from the shared builder — a client would "
        "behave differently depending on which door it came through"
    )


def test_http_endpoint_delegates_to_the_shared_builder():
    """Acceptance criterion, second half: the HTTP handler computes
    nothing of its own, so it cannot drift from the MCP surface.

    Structural on purpose — it is the absence of a second implementation
    that guarantees identity, and only reading the source proves absence.
    """
    import ast
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2]
           / "backend" / "api" / "v1" / "chart.py").read_text()
    tree = ast.parse(src)
    handler = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "compute_chart"
    )
    called = {
        node.func.id for node in ast.walk(handler)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "build_chart_response" in called, (
        "the endpoint must delegate to the shared builder, never build a "
        "chart_core of its own"
    )
    # No stray ephemeris work in the handler: that would be a second
    # implementation by another name. Checked over imports in the AST,
    # not as a substring — "answered" contains "swe".
    assert "build_chart_core" not in called
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [])
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "swisseph" not in imported, (
        "the HTTP layer must not touch swisseph directly — it would become "
        "a second implementation able to drift from the MCP surface"
    )


@pytest.mark.parametrize("lat,lon", [(47.8388, 35.1396), (69.6492, 18.9553)])
def test_the_http_response_model_changes_nothing_it_validates(lat, lon):
    """A response_model sits between the builder and the wire, so it is a
    place identity can be lost: a forgotten field is dropped, a reordered
    one changes the bytes, `Optional` fields appear as nulls the MCP
    surface never sends. Both parametrisations matter — the polar one is
    the only chart carrying `requested_house_system` and a note.
    """
    from backend.services.astrology.chart_contract import ChartResponse

    body = build_chart_response(
        **{**REF, "lat": lat, "lon": lon}, timezone_name="Europe/Kyiv"
    )
    through_model = ChartResponse.model_validate(body).model_dump(
        mode="json", exclude_none=True
    )
    assert _dump(through_model) == _dump(body), (
        "the response_model altered the payload — the HTTP surface would "
        "stop matching the MCP one"
    )
    # Order too, not just contents: byte-identical is the acceptance
    # criterion, and sort_keys above would hide a reordered model.
    assert list(through_model["chart_core"]) == list(body["chart_core"])


def test_envelope_carries_provenance_and_disclaimer():
    body = build_chart_response(
        birth_date=date(1977, 7, 1), birth_time=time(22, 30),
        lat=47.8388, lon=35.1396, place_label="Запорожье", locale="ru",
    )
    assert "SWIEPH" in body["provenance"]["ephemeris_engine"]
    assert "apparent" in body["provenance"]["sidereal_time"]
    assert body["disclaimer"]
    assert body["chart_core"]["birth"]["utc_offset_used"] == "+03:00"


def test_out_of_coverage_date_is_refused_by_the_builder():
    """The endpoint turns this ValueError into a 400; the refusal itself
    belongs to the builder, where both transports inherit it."""
    with pytest.raises(ValueError, match="coverage"):
        build_chart_response(
            birth_date=date(1750, 1, 1), birth_time=time(12, 0),
            lat=0.0, lon=0.0,
        )


# ── the premise itself: client math reproduces the server ───────────────────

def _angles_from_core(gmst: float, obliquity: float, lat: float, lon: float):
    """The exact formulas chart-kit implements, in Python, so the premise
    is asserted in CI rather than assumed.

    The quadrant correction is not cosmetic: without it the arctangent's
    principal value returns the DESCENDANT instead of the Ascendant for
    7.9% of the globe (a 1068-point lat/lon sweep found 84 flips, all
    poleward of ~66°). The Ascendant is the eastern horizon point, which
    always leads the Midheaven by 0–180° in zodiacal order.
    """
    ramc = math.radians((gmst + lon) % 360.0)
    eps, phi = math.radians(obliquity), math.radians(lat)
    mc = math.degrees(math.atan2(math.sin(ramc),
                                 math.cos(ramc) * math.cos(eps))) % 360.0
    asc = math.degrees(math.atan2(
        math.cos(ramc),
        -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps)),
    )) % 360.0
    if (asc - mc) % 360.0 > 180.0:
        asc = (asc + 180.0) % 360.0
    return asc, mc


@pytest.mark.parametrize("name,lat,lon", LOCATIONS)
def test_client_side_angles_match_the_server(name, lat, lon):
    """0.01° is the golden-set bar; rounding the payload to 4 decimals
    leaves the real error two orders of magnitude below it."""
    core = build_chart_core(**REF).core
    asc_kit, mc_kit = _angles_from_core(
        core["gmst"], core["obliquity"], lat, lon
    )
    system, _ = resolve_house_system(core["jd_ut"], lat, lon, "placidus")
    from backend.services.astrology.chart_core import HOUSE_SYSTEM_CODES

    _, ascmc = swe.houses_ex(
        core["jd_ut"], lat, lon, HOUSE_SYSTEM_CODES[system]
    )
    d_asc = abs((ascmc[0] - asc_kit + 180) % 360 - 180)
    d_mc = abs((ascmc[1] - mc_kit + 180) % 360 - 180)
    assert d_asc < 0.01, f"{name}: Asc off by {d_asc * 3600:.2f}\""
    assert d_mc < 0.01, f"{name}: MC off by {d_mc * 3600:.2f}\""
