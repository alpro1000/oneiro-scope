"""Swiss Ephemeris must serve SWIEPH on every thread, not just the importer's.

pyswisseph keeps the C library's state thread-local in this build. The path is
set once, at `backend.core.ephemeris` import, on whichever thread imported it —
and on any other thread the library finds no data files and falls back to
Moshier. It does not raise. It returns a plausible number with SEFLG_MOSEPH in
the flags:

    main thread   swe.calc_ut(...) -> flags 258  (SWIEPH|SPEED)
    worker thread swe.calc_ut(...) -> flags 260  (MOSEPH|SPEED)

`calc_ut_swieph` reads those flags and refuses, so the guarded path fails
closed — but roughly twenty direct `swe.calc_ut` / `swe.houses` call sites
across the astrology services do not check, and would publish Moshier
positions under a `"Swiss Ephemeris 2.10.03 (SWIEPH)"` provenance stamp at
confidence 1.0. That is the exact shape conventions.md §12 forbids: a
degradation indistinguishable from a correct answer.

Nothing in production offloads ephemeris work to a thread *today*. That is a
property of the current code, not of the design — `fastapi.testclient` already
runs the app on a portal thread, which is how `test_lunar_endpoint.py` came to
answer 500 — so the invariant is pinned here rather than left to be
rediscovered by whoever adds the first `run_in_executor`.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time

import pytest

swe = pytest.importorskip("swisseph", reason="pyswisseph not installed")

from backend.core import ephemeris as ephe_config  # noqa: E402

# A moment with no special significance: mid-range for the shipped *_18.se1
# files and far from any boundary.
BIRTH = dict(
    birth_date=date(1990, 5, 15),
    birth_time=time(14, 30),
    lat=55.7558,
    lon=37.6173,
    place_label="Moscow",
    timezone_name="Europe/Moscow",
)
JD_UT = 2460371.0  # 2024-03-01 12:00 UT


def _on_worker(fn, *args, **kwargs):
    """Run `fn` on a thread that is definitely not the importing one."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(fn, *args, **kwargs).result()


def test_the_thread_local_fallback_is_real_and_not_hypothetical():
    """Guard the premise: without binding, a worker thread gets Moshier.

    If a future pyswisseph makes the state process-global this goes green in
    the other direction and the `bind_thread` calls become dead weight — worth
    knowing, and worth deleting them deliberately rather than by guess.
    """
    def unbound_flags():
        # Deliberately NOT calling bind_thread: this measures the raw library.
        _, flags = swe.calc_ut(JD_UT, swe.SUN, ephe_config.FLAGS)
        return flags

    flags = _on_worker(unbound_flags)
    if flags & swe.FLG_SWIEPH:
        pytest.skip(
            "this pyswisseph build shares ephemeris state across threads; the "
            "bind_thread() calls are harmless but no longer load-bearing"
        )
    assert flags & swe.FLG_MOSEPH, f"unexpected flags {flags} off the main thread"


def test_bind_thread_restores_swieph_on_a_worker():
    def bound_flags():
        ephe_config.bind_thread()
        _, flags = swe.calc_ut(JD_UT, swe.SUN, ephe_config.FLAGS)
        return flags

    assert _on_worker(bound_flags) & swe.FLG_SWIEPH


def test_the_guarded_helper_no_longer_raises_off_the_main_thread():
    """`calc_ut_swieph` used to turn this into a 500 (lunar endpoint)."""
    main = ephe_config.calc_ut_swieph(JD_UT, swe.SUN)
    worker = _on_worker(ephe_config.calc_ut_swieph, JD_UT, swe.SUN)
    assert worker[0] == pytest.approx(main[0], abs=1e-9)


def test_a_natal_chart_is_the_same_object_on_either_thread():
    """The payload, not just the flags — this is what a client receives."""
    from backend.services.astrology.chart_core import build_chart_response

    main = build_chart_response(**BIRTH)["chart_core"]
    worker = _on_worker(lambda: build_chart_response(**BIRTH)["chart_core"])
    assert json.dumps(worker, sort_keys=True) == json.dumps(main, sort_keys=True)


def test_the_unguarded_services_agree_across_threads():
    """The call sites that read no flags and so could never have complained."""
    from backend.services.astrology.astrocartography import acg_lines, natal_planets
    from backend.services.astrology.solar_return import solar_return
    from backend.services.astrology.transits_engine import find_transits
    from backend.services.lunar.engine import compute_lunar
    from backend.services.strategic.pattern_engine import money_contour, natal_geometry

    geo_args = dict(
        birth_date="1990-05-15", birth_time="14:30",
        birth_timezone="Europe/Moscow", lat=55.7558, lon=37.6173,
    )

    cases = {
        "natal_planets": lambda: natal_planets(JD_UT),
        "acg_lines": lambda: acg_lines(JD_UT),
        "natal_geometry": lambda: natal_geometry(**geo_args),
        "money_contour": lambda: money_contour(natal_geometry(**geo_args)),
        "solar_return": lambda: solar_return(
            natal_geometry(**geo_args)["jd_ut"], 2026, 55.7558, 37.6173,
        ),
        "find_transits": lambda: find_transits(
            natal_geometry(**geo_args)["jd_ut"],
            date(2026, 1, 1), date(2026, 3, 1),
        ),
        "compute_lunar": lambda: compute_lunar("2024-03-01", "UTC").jd_ut,
    }

    for name, call in cases.items():
        main = json.dumps(call(), sort_keys=True, default=str)
        worker = json.dumps(_on_worker(call), sort_keys=True, default=str)
        assert worker == main, f"{name} differs between threads — Moshier leak"
