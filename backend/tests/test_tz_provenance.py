"""`tz_source` must say who chose the timezone — the caller or us.

Found by the owner reading a live response: a chart computed WITHOUT a
`timezone_name` came back with `tz_source: "explicit"`. The zone itself was
right (Europe/Kyiv, +03:00 — Soviet decree time, correct for July 1977), but
the provenance field claimed the caller had vouched for it when the server had
derived it from the coordinates.

The two are different claims and carry different risk. A caller-named zone is
an assertion that can be wrong, and being wrong is expensive: an hour of
timezone error moves the MC by ~15°, against ~1° per degree of longitude. A
zone we looked up from the coordinates is our own tzdata result, reproducible
from the same inputs. A reader who cannot tell them apart cannot judge the
chart's angles — which is the whole point of shipping provenance.

Cause: `service.py` pre-resolved the zone and passed it down as if it were the
request's, so by the time `resolve_birth_moment` saw it, a derived zone was
indistinguishable from a supplied one.
"""

from __future__ import annotations

import asyncio
from datetime import date, time

import pytest

from backend.services.astrology.schemas import NatalChartRequest
from backend.services.astrology.service import AstrologyService

# 1977-07-01 22:30 in Zaporizhzhia. Chosen because the offset is a real trap:
# the USSR ran decree time (UTC+3) year-round and did not adopt summer time
# until 1981, so a naive "+04:00 in July" is wrong by an hour.
REF = dict(
    birth_date=date(1977, 7, 1),
    birth_time=time(22, 30),
    birth_place="Запорожье, Украина",
    locale="ru",
    latitude=47.85167,
    longitude=35.11714,
)


def _birth(timezone_name=None):
    svc = AstrologyService()
    req = NatalChartRequest(**REF, timezone_name=timezone_name)
    resp = asyncio.run(svc.calculate_natal_chart(req, interpret=False))
    return resp.chart_core["birth"]


def test_a_derived_zone_is_labelled_derived():
    """No `timezone_name` in the request → the server looked it up."""
    birth = _birth()
    assert birth["tz_source"] == "coordinates", (
        "the caller named no zone, so claiming 'explicit' credits them with a "
        "decision the server made"
    )


def test_a_caller_supplied_zone_is_labelled_explicit():
    birth = _birth("Europe/Kyiv")
    assert birth["tz_source"] == "explicit"


def test_the_label_changes_but_the_zone_does_not():
    """The fix must be about honesty, not about a different answer.

    Both paths run the same TimezoneFinder lookup over the same coordinates,
    so the computed chart is byte-identical — only the provenance differs.
    """
    derived, supplied = _birth(), _birth("Europe/Kyiv")
    assert derived["tz_used"] == supplied["tz_used"] == "Europe/Kyiv"
    assert derived["utc_offset_used"] == supplied["utc_offset_used"]
    assert derived["utc"] == supplied["utc"]
    assert derived["tz_source"] != supplied["tz_source"]


def test_decree_time_is_still_right():
    """Guards the fix itself: rerouting the timezone must not reintroduce the
    classic off-by-an-hour for the Soviet period."""
    birth = _birth()
    assert birth["utc_offset_used"] == "+03:00", "1977 USSR: decree time, no DST"
    assert birth["utc"].startswith("1977-07-01T19:30")


@pytest.mark.parametrize("bad", ["Europe/Nowhere", "MSK", "GMT+3"])
def test_an_unknown_named_zone_is_refused_not_substituted(bad):
    """§12: a bad explicit zone must fail loudly. Silently falling back to UTC
    would move every angle by three hours and still label it 'explicit'.

    The refusal happens at the CONTRACT boundary — `NatalChartRequest` rejects
    the value before any computation starts — which is earlier and better than
    failing inside the service. `MSK` and `GMT+3` are in the set because they
    look like timezones to a human and are not IANA zones; a caller reaching
    for either gets told what to write instead.
    """
    with pytest.raises(ValueError, match="not a known IANA zone"):
        NatalChartRequest(**REF, timezone_name=bad)
