"""The field names the MCP App views read must be the ones the server emits.

This file exists because of a specific, quiet failure. `relocations.ts`
declared `orb?: number` while `compare_relocations` emits `orb_deg`, so every
contact rendered as `орб 0.00°` — and, because these views hand their figures
to the chat through `ui/message`, that fabricated exactness was sent to the
model as if it were measured. A view that prints a wrong number is a display
bug; a view that *tells the model* a wrong number pretends to be the
deterministic layer (confidence 1.0) while inventing.

TypeScript cannot catch this: the interfaces are the view's BELIEF about a
JSON response, and `tsc` happily checks that belief against itself. Nothing
connects them to the Python that produces the payload — except this.

So the assertions here are deliberately about NAMES, not values, and each one
names the view that reads it. When a payload key is renamed, this goes red
next to the file that has to change with it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.services.astrology.astrocartography import compare_locations, natal_planets
from backend.services.strategic.pattern_engine import (
    money_contour,
    natal_geometry,
    vocation_map,
)

VIEWS = Path(__file__).resolve().parents[2] / "packages" / "mcp-app" / "src"

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


# --- relocations.ts -----------------------------------------------------------


@pytest.fixture(scope="module")
def relocations(geo):
    return compare_locations(
        geo["jd_ut"],
        [("Zaporizhzhia", 47.85167, 35.11714), ("London", 51.5074, -0.1278)],
        orb_deg=8.0,
    )


def test_an_angle_hit_names_its_orb_orb_deg(relocations):
    """`relocations.ts` reads `h.orb_deg`. It read `h.orb` and got 0.00°."""
    hits = [h for loc in relocations for h in loc["angle_hits"]]
    assert hits, "fixture chart produced no angle hits — pick another"
    for h in hits:
        assert "orb_deg" in h, f"angle_hit lost orb_deg: {sorted(h)}"
        assert "orb" not in h, "server now emits `orb` — relocations.ts reads orb_deg"
        assert isinstance(h["orb_deg"], (int, float))


def test_a_location_carries_the_caveat_the_view_prints(relocations):
    """The score is not a ranking, and `score_explanation` is where it says so."""
    for loc in relocations:
        assert {"name", "latitude", "longitude", "angles", "angle_hits", "score"} \
            <= set(loc)
        expl = loc["score_explanation"]
        # The view shows `total_significance` beside `score` precisely because
        # the score weighs Mercury/Uranus/Neptune at 0 whatever their orb.
        assert "plain" in expl and "total_significance" in expl


def test_the_view_does_not_read_a_field_named_orb(relocations):
    src = (VIEWS / "relocations.ts").read_text(encoding="utf-8")
    assert "h.orb_deg" in src
    assert "h.orb ?" not in src and "orb?: number" not in src


def test_the_view_keeps_the_servers_order(relocations):
    """`compare_locations` documents itself as comparison, not ranking.

    Sorting by `score` in the view would have re-labelled "unscored" as
    "weakest" — the exact misreading `score_explanation` warns against.
    """
    assert [loc["name"] for loc in relocations] == ["Zaporizhzhia", "London"]
    src = (VIEWS / "relocations.ts").read_text(encoding="utf-8")
    assert ".sort(" not in src, "the view must not re-order the server's places"


# --- pattern-map.ts -----------------------------------------------------------


def test_mc_conjunctions_are_contacts_not_placements(geo):
    """`mc.conjunct` is `{planet, orb_deg}`.

    Rendered through the placement renderer it printed "☉ sun — —" and dropped
    the orb — the one figure that says how tight the contact is.
    """
    mc = vocation_map(geo)["mc"]
    assert {"sign", "rulers", "conjunct"} <= set(mc)
    for c in mc["conjunct"]:
        assert set(c) == {"planet", "orb_deg"}, (
            f"mc.conjunct changed shape: {sorted(c)} — pattern-map.ts renders "
            "planet + orb_deg and nothing else"
        )
    # Rulers ARE placements, and the view is right to render them as such.
    for r in mc["rulers"]:
        assert "planet" in r and "sign" in r


def test_the_linchpin_has_two_shapes_and_the_view_handles_both(geo):
    """`same_ruler` carries `planet` alone — no pair, no separation."""
    lp = money_contour(geo)["linchpin"]
    assert "linked" in lp
    if lp.get("type") == "same_ruler":
        assert "planet" in lp and "ruler_2nd" not in lp
    else:
        assert {"ruler_2nd", "ruler_8th", "separation_deg"} <= set(lp)

    # Both branches must exist in the renderer regardless of which one this
    # particular fixture chart happens to produce.
    src = (VIEWS / "pattern-map.ts").read_text(encoding="utf-8")
    assert "same_ruler" in src, "the view ignores the stronger linchpin shape"
    assert "lp.ruler_2nd" in src


def test_part_of_fortune_dispositor_is_a_placement(geo):
    """Typing this as a string is what white-screened the view via `esc()`."""
    pof = money_contour(geo)["part_of_fortune"]
    disp = pof.get("dispositor")
    if disp is not None:
        assert isinstance(disp, dict) and "planet" in disp


def test_the_view_claims_only_the_patterns_it_can_draw():
    """Six tools share the `_base()` envelope; this view renders two of them.

    `pattern_id && computed` accepted all six, and `render` has two branches —
    so a decade map would have been drawn under the heading "Money contour".
    """
    src = (VIEWS / "pattern-map.ts").read_text(encoding="utf-8")
    assert "p.pattern_id === 'money-contour'" in src
    assert "p.pattern_id === 'vocation-map'" in src


def test_the_two_patterns_really_do_share_one_envelope(geo):
    """The premise for one view serving two tools."""
    m, v = money_contour(geo), vocation_map(geo)
    assert "part_of_fortune" in m
    assert {"mc", "work_houses", "dignified"} <= set(v)


# --- acg-map.ts --------------------------------------------------------------


@pytest.fixture(scope="module")
def acg(geo):
    from backend.services.astrology.astrocartography import acg_lines

    return acg_lines(geo["jd_ut"])


def _view_window() -> tuple[float, float]:
    """LAT_TOP / LAT_BOTTOM as the view actually declares them."""
    src = (VIEWS / "acg-geometry.ts").read_text(encoding="utf-8")
    found = dict(re.findall(r"export const (LAT_TOP|LAT_BOTTOM) = (-?\d+);", src))
    assert set(found) == {"LAT_TOP", "LAT_BOTTOM"}, found
    return float(found["LAT_TOP"]), float(found["LAT_BOTTOM"])


def test_the_map_reads_planet_and_angle_off_every_feature(acg):
    """`acg-map.ts` colours by `properties.planet` and dashes by `.angle`."""
    features = acg["features"]
    assert features, "no lines computed for the fixture chart"
    for f in features:
        assert set(f["properties"]) >= {"planet", "angle"}, sorted(f["properties"])
        assert f["geometry"]["type"] == "LineString"
        for lon, lat in f["geometry"]["coordinates"]:
            # GeoJSON order. Transposed, the whole map would be drawn sideways
            # and nothing would raise.
            assert -180.0 <= lon <= 180.0, f"longitude out of range: {lon}"
            assert -90.0 <= lat <= 90.0, f"latitude out of range: {lat}"


def test_every_angle_family_survives_the_views_latitude_window(acg):
    """The meridians were silently dropped, and this is the shape of that bug.

    MC/IC come back as TWO-point LineStrings spanning -58…80, while the view
    clips at -58…78. The old clip discarded out-of-window points instead of
    truncating the segment, which left one point, which `run.length > 1`
    rejected — so every MC and IC line vanished while the legend and the
    "N lines" footer still counted them.

    The clip is fixed in `acg-geometry.ts` (and unit-tested there). This
    asserts the other half: that each angle family still has geometry INSIDE
    the window at all, so a future change to the server's latitude span cannot
    empty the map from the other side.
    """
    top, bottom = _view_window()
    seen: dict[str, int] = {}
    for f in acg["features"]:
        angle = f["properties"]["angle"]
        crosses = any(bottom <= lat <= top for _lon, lat in f["geometry"]["coordinates"])
        if not crosses:
            # A segment can still be drawable while both endpoints sit outside,
            # provided they straddle the window — which is exactly the meridian
            # case, so count it as present.
            lats = [lat for _lon, lat in f["geometry"]["coordinates"]]
            crosses = min(lats) < bottom and max(lats) > top
        seen[angle] = seen.get(angle, 0) + int(crosses)

    assert set(seen) == {"MC", "IC", "Asc", "Desc"}, sorted(seen)
    for angle, drawable in seen.items():
        assert drawable, (
            f"no {angle} line has any geometry inside the view's latitude "
            f"window {bottom}…{top} — the map would silently omit them"
        )


# --- the property that makes all of the above matter --------------------------


@pytest.mark.parametrize(
    "view", ["relocations.ts", "pattern-map.ts", "natal-wheel.ts", "acg-map.ts",
             "lunar-month.ts", "dream-evidence.ts"],
)
def test_no_view_substitutes_a_zero_for_a_missing_figure(view):
    """`(v ?? 0).toFixed(n)` prints an absent value as a measurement.

    That is how `орб 0.00°` reached the chat. A missing number must render as
    a missing number — the views use a `num`/`deg` helper that returns an em
    dash — so this pattern is banned outright rather than reviewed case by
    case.
    """
    src = (VIEWS / view).read_text(encoding="utf-8")
    offenders = []
    for line in src.splitlines():
        code = line.strip()
        # Comments may quote the banned pattern in order to explain it — and
        # the helper that replaces it does exactly that, a few lines up.
        if code.startswith(("*", "//", "/*")):
            continue
        if "?? 0)" in code and "toFixed" in code:
            offenders.append(code)
    assert not offenders, (
        f"{view} substitutes 0 for a missing figure and would send it to the "
        f"chat as fact:\n  " + "\n  ".join(offenders)
    )
