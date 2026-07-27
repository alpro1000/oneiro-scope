"""The two chart engines must agree on which lunar node they mean.

`astrology/ephemeris.py` has always used the TRUE node (swisseph body 11);
`strategic/pattern_engine.py` used the MEAN node. On the same chart the two
differ by up to ~1.8 deg — enough to place the node in a different house and to
make `calculate_natal_chart` and `money_contour` disagree about the same person.
Verified live 2026-07: true 200.828 deg vs mean 200.257 deg for 1977-07-01.
"""

from __future__ import annotations

import swisseph as swe

from backend.services.astrology.ephemeris import PLANET_CODES as EPHEMERIS_IDS
from backend.services.strategic.pattern_engine import PLANET_IDS as STRATEGIC_IDS


def test_strategic_engine_uses_the_true_node():
    assert "north_node" in STRATEGIC_IDS, "node key should be named for the point, not the method"
    assert "mean_node" not in STRATEGIC_IDS, "mean node was the inconsistency — it should be gone"
    assert STRATEGIC_IDS["north_node"] == swe.TRUE_NODE


def test_both_engines_request_the_same_body():
    """Whatever the key names, the swisseph body must be identical."""
    ephemeris_node = next(
        code for planet, code in EPHEMERIS_IDS.items() if "node" in str(planet).lower()
    )
    assert STRATEGIC_IDS["north_node"] == ephemeris_node == swe.TRUE_NODE


def test_true_and_mean_node_actually_differ_enough_to_matter():
    """Guards the premise: if they were equivalent this alignment would be moot."""
    jd = swe.julday(1977, 7, 1, 19.5)  # 1977-07-01 19:30 UT
    flags = swe.FLG_MOSEPH | swe.FLG_SPEED
    true_lon = swe.calc_ut(jd, swe.TRUE_NODE, flags)[0][0]
    mean_lon = swe.calc_ut(jd, swe.MEAN_NODE, flags)[0][0]
    assert abs(true_lon - mean_lon) > 0.1
