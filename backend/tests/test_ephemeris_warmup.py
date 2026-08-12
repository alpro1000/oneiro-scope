"""The first chart after a restart must not be the slow one.

Production, three identical calls: the first FAILED, the second took 11403 ms,
the third — six seconds later, same input, `cache_hit: false` on both — took
32.2 ms. Geocoding was ruled out (coordinates were passed), the database was
ruled out (the third call takes the same path), the cache was ruled out (it
does not exist). What is left is the one thing a chart does and `/health` does
not: read the .se1 files.

The import-time probe was never going to prevent this. It computes three
bodies at J2000 — enough to prove the files are readable, which is its job,
and almost nothing a 1977 chart touches: different bodies, different region of
the same file. Locally the first-versus-third gap is 2.370 ms → 0.006 ms, 380x
on an SSD; on Render's network-backed disk that ratio is the eleven seconds.

The user-visible half was worse than the latency. The first call after a
restart did not wait — it failed. That is the catalog-review scenario exactly:
a reviewer tries once and closes the application.
"""

from __future__ import annotations

import pytest

swe = pytest.importorskip("swisseph", reason="pyswisseph not installed")

from backend.core.ephemeris import (  # noqa: E402
    _WARM_BODIES,
    _WARM_JDS,
    calc_ut_swieph,
    warm_ephemeris,
)


def test_the_warm_up_covers_every_body_a_chart_computes():
    """Warming a subset would leave the gap open for the bodies it missed —
    which is precisely how the import probe failed to help."""
    from backend.services.astrology import chart_core

    source = (
        __import__("pathlib").Path(chart_core.__file__).read_text()
        if hasattr(chart_core, "__file__") else ""
    )
    # Every body the chart module names must be in the warm set. Checked by
    # name rather than by running a chart, so this stays fast and does not
    # depend on a birth-data fixture.
    for name in ("SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER",
                 "SATURN", "URANUS", "NEPTUNE", "PLUTO"):
        if f"swe.{name}" in source or name.lower() in source.lower():
            assert getattr(swe, name) in _WARM_BODIES, (
                f"{name} is computed by charts but never warmed — the first "
                f"chart after a restart pays for it"
            )


def test_the_warm_up_spans_the_birth_years_people_enter():
    """One Julian day warms one region of the file. The owner's own chart is
    1977; a warm set clustered on today would repeat the original mistake."""
    assert len(_WARM_JDS) >= 3
    # ~1940 to ~2020 in Julian days, the range real birth dates fall in.
    assert min(_WARM_JDS) < 2434000, "nothing warmed before ~1952"
    assert max(_WARM_JDS) > 2452000, "nothing warmed after ~2001"


def test_warming_returns_a_measurable_cost():
    """It reports its own price so the startup log can show it. A warm-up
    nobody can see the cost of is a warm-up nobody will notice breaking."""
    spent = warm_ephemeris()
    assert isinstance(spent, float)
    assert spent >= 0.0


def test_a_chart_is_fast_once_warmed():
    """The property that matters, stated as a ratio rather than a deadline:
    absolute timings depend on the disk (SSD here, network volume in
    production), but "the first chart costs about what the next one costs"
    holds on both — and is exactly what was false before."""
    import time

    warm_ephemeris()

    jd_1977 = 2443326.3125  # the owner's chart, 1977-07-01 19:30 UT

    def one_pass() -> float:
        started = time.perf_counter()
        for body in _WARM_BODIES:
            calc_ut_swieph(jd_1977, body)
        return time.perf_counter() - started

    first, second = one_pass(), one_pass()
    # Generous factor: CI machines are noisy and this is a page-cache
    # assertion, not a benchmark. Before the warm-up the ratio was ~380x.
    assert first < max(second, 1e-6) * 50, (
        f"first pass {first * 1000:.3f} ms vs second {second * 1000:.3f} ms — "
        f"the chart path is still cold after warm_ephemeris()"
    )


def test_the_probe_stays_cheap():
    """Integrity and warmth are separate jobs on purpose. The probe runs on
    every import — tests, CLI tools, every worker — so it must stay three
    bodies at one date; the warm-up is what the SERVER calls."""
    import inspect

    from backend.core import ephemeris

    probe = inspect.getsource(ephemeris._startup_probe)
    assert "for jd in" not in probe, "the probe grew a loop over dates"
    assert probe.count("swe.") <= 4, "the probe is warming, not probing"
