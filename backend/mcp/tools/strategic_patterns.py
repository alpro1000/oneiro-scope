"""Analysis-pattern MCP tools (patterns catalog → callable surface).

One tool per pattern in
`backend/services/strategic/knowledge_base/analysis_patterns.json`.
Each returns DETERMINISTIC data (astronomy 1.0, or physiognomy
dictionary 0.6) plus a pointer to the catalog entry whose
`interprets.rules` the consuming skill applies at the symbolic layer
(0.8). Tools never interpret; skills do — labelled.

Birth place is passed as lat/lon/timezone: resolve city names first via
`search_city` / `validate_birth_data` (geo tools), per the layering rule.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.mcp.tools._menu import (
    BIRTH_DATE,
    BIRTH_PLACE,
    BIRTH_TIME,
    TARGET_DATE,
    TRAITS,
    with_menu,
)
from backend.services.strategic.analysis_plan import build_plan
from backend.services.strategic.disclaimer import DISCLAIMERS, DISCLAIMER_RU
from backend.services.strategic.pattern_engine import (
    decade_map as _decade_map,
    electional_day as _electional_day,
    life_pivots as _life_pivots,
    money_contour as _money_contour,
    natal_geometry,
    reverse_physiognomy as _reverse_physiognomy,
    vocation_map as _vocation_map,
)

_CATALOG = "backend/services/strategic/knowledge_base/analysis_patterns.json"


def _base(
    pattern_id: str, layer: str, confidence: float, locale: str = "ru"
) -> dict[str, Any]:
    """Common envelope. `locale` picks the disclaimer language for tools that
    return user-facing text — a Russian disclaimer under an English plan is a
    contract violation, not a cosmetic one."""
    return {
        "pattern_id": pattern_id,
        "layer": layer,
        "confidence": confidence,
        "interpretation_rules_ref": f"{_CATALOG}#{pattern_id}",
        "disclaimer": DISCLAIMERS.get(locale, DISCLAIMER_RU),
    }


def analysis_plan(
    known_inputs: Optional[list[str]] = None,
    completed_stages: Optional[list[str]] = None,
    locale: str = "ru",
) -> dict[str, Any]:
    """List everything this server can compute, in the order a reading is built.

    CALL THIS FIRST when a user asks for astrology/dream/face analysis and you
    are unsure what to offer. It answers three questions at once: what can run
    with the inputs you already have, what is blocked and on which input, and
    which single step comes next. Then work down `ready` in order, or ask the
    questions in `questions_to_ask` to unblock more.

    The plan is deterministic data — no interpretation. Stage names and
    questions come back in the requested language so they can be shown as-is.

    Args:
        known_inputs: input keys already collected. Recognised keys:
            "birth_date", "birth_time", "birth_place", "target_date",
            "start_year", "scan_years", "cities", "partner_birth_data",
            "dream_text", "face_photos", "character_traits".
        completed_stages: stage ids already run in this conversation (e.g.
            ["natal-chart"]) so they stop being offered as the next step.
        locale: "ru" (default) or "en".
    """
    out = _base("analysis-plan", "astronomy", 1.0, locale=locale)
    out.pop("interpretation_rules_ref", None)
    out["computed"] = build_plan(known_inputs, completed_stages, locale)
    out["how_to_use"] = (
        "Take `next_step`, call its `tool`; if `questions_to_ask` is non-empty, "
        "ask those first. Re-call with `completed_stages` to advance."
    )
    return out


def money_contour(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    lat: float,
    lon: float,
) -> dict[str, Any]:
    """Compute the structural money contour of a natal chart.

    Returns 2nd/8th/11th house cusp signs, rulers with placements and
    classical dignities, occupants, the ruler-of-2nd × ruler-of-8th
    "linchpin" (same planet or tight conjunction = personal and shared
    money share one engine), Part of Fortune (sect-aware) with its
    dispositor. Data only — the money-contour skill applies the catalog
    interpretation rules on top.

    Args:
        birth_date: YYYY-MM-DD of birth.
        birth_time: HH:MM or HH:MM:SS local birth time.
        birth_timezone: IANA tz of the birth place (e.g. "Europe/Kyiv").
        lat: birth latitude, degrees.
        lon: birth longitude, degrees.
    """
    geo = natal_geometry(birth_date, birth_time, birth_timezone, lat, lon)
    out = _base("money-contour", "astronomy", 1.0)
    out["computed"] = _money_contour(geo)
    out["provenance"] = geo["provenance"]
    return with_menu(
        out, domain="astro",
        known_inputs=[BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE],
        completed=["money-contour"],
    )


def vocation_map(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    lat: float,
    lon: float,
) -> dict[str, Any]:
    """Compute vocation signals of a natal chart (for profession clusters).

    Returns MC sign + rulers with placements, planets conjunct MC
    (orb ≤8°), the 2nd/6th/10th work-house blocks, planets in essential
    dignity (domicile/exaltation), angular planets (houses 1/4/7/10) and
    Part of Fortune. The vocation-map skill clusters these into 3-5
    profession families citing each placement.

    Args:
        birth_date: YYYY-MM-DD of birth.
        birth_time: HH:MM or HH:MM:SS local birth time.
        birth_timezone: IANA tz of the birth place.
        lat: birth latitude, degrees.
        lon: birth longitude, degrees.
    """
    geo = natal_geometry(birth_date, birth_time, birth_timezone, lat, lon)
    out = _base("vocation-map", "astronomy", 1.0)
    out["computed"] = _vocation_map(geo)
    out["provenance"] = geo["provenance"]
    return with_menu(
        out, domain="astro",
        known_inputs=[BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE],
        completed=["vocation-map"],
    )


def decade_map(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    lat: float,
    lon: float,
    start_year: int,
    years: int = 10,
) -> dict[str, Any]:
    """Compute a year-by-year decade map of slow-planet transits.

    For each year: Jupiter..Pluto placements (sign + natal house
    transited, July-1 snapshot) and dated aspect hits (orb ≤1.5°,
    monthly grid) to natal planets and angles, with saturn_return /
    jupiter_return / angle_crossing flags. The decade-map skill groups
    years into phase blocks and names launch/harvest windows.

    Args:
        birth_date: YYYY-MM-DD of birth.
        birth_time: HH:MM or HH:MM:SS local birth time.
        birth_timezone: IANA tz of the birth place.
        lat: birth latitude, degrees.
        lon: birth longitude, degrees.
        start_year: first year of the map (e.g. 2026).
        years: how many years to map, 1-12 (default 10).
    """
    geo = natal_geometry(birth_date, birth_time, birth_timezone, lat, lon)
    out = _base("decade-map", "astronomy", 1.0)
    out["computed"] = _decade_map(geo, start_year, years)
    out["provenance"] = geo["provenance"]
    return with_menu(
        out, domain="astro",
        known_inputs=[BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE],
        completed=["decade-map"],
    )


def life_pivots(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    lat: float,
    lon: float,
    from_year: int,
    to_year: int,
) -> dict[str, Any]:
    """Scan past years for dated life-pivot windows (retro-validation).

    Monthly scan of Saturn/Uranus/Neptune/Pluto conjunctions (orb ≤1°)
    to natal ASC/MC/IC/DSC/Sun/Moon, deduped into dated windows with
    relocation markers (IC = strong, ASC/Moon = possible), plus Saturn
    return and Uranus opposition cycles with ages, plus per-window
    validation questions for the user. Confirmed windows upgrade the
    insight to astronomy + user_context convergence (HIGH) — see the
    catalog validation_loop.

    Args:
        birth_date: YYYY-MM-DD of birth.
        birth_time: HH:MM or HH:MM:SS local birth time.
        birth_timezone: IANA tz of the birth place.
        lat: birth latitude, degrees.
        lon: birth longitude, degrees.
        from_year: scan start year (inclusive).
        to_year: scan end year (inclusive); window capped at 60 years.
    """
    geo = natal_geometry(birth_date, birth_time, birth_timezone, lat, lon)
    out = _base("life-pivots", "astronomy", 1.0)
    out["computed"] = _life_pivots(geo, from_year, to_year)
    out["provenance"] = geo["provenance"]
    return with_menu(
        out, domain="astro",
        known_inputs=[BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE],
        completed=["life-pivots"],
    )


def electional_day(
    birth_date: str,
    birth_time: str,
    birth_timezone: str,
    lat: float,
    lon: float,
    target_date: str,
    target_timezone: str,
    day_start_hour: int = 6,
    day_end_hour: int = 22,
    step_minutes: int = 30,
) -> dict[str, Any]:
    """Compute hour-by-hour electional data for one target day.

    Per step: Moon position/sign and aspects (orb ≤1°) to natal
    Sun/Moon/Mercury/Venus/Mars/ASC/MC with harmonious/tense nature.
    Plus: Moon phase (waxing = beginnings, waning = release), Mercury
    retrograde flag (contract caution), sign-ingress time and the
    void-of-course window (after the last exact Ptolemaic aspect before
    ingress — traditionally "avoid final commitments"). The
    electional-day skill turns this into best/avoid hour advice.

    Args:
        birth_date: YYYY-MM-DD of birth.
        birth_time: HH:MM or HH:MM:SS local birth time.
        birth_timezone: IANA tz of the birth place.
        lat: birth latitude, degrees.
        lon: birth longitude, degrees.
        target_date: YYYY-MM-DD day to elect hours in.
        target_timezone: IANA tz the user acts in (e.g. "Europe/Prague").
        day_start_hour: first local hour of the grid (default 6).
        day_end_hour: last local hour of the grid (default 22).
        step_minutes: grid step in minutes (default 30).
    """
    geo = natal_geometry(birth_date, birth_time, birth_timezone, lat, lon)
    out = _base("electional-day", "astronomy", 1.0)
    out["computed"] = _electional_day(
        geo, target_date, target_timezone,
        day_start=day_start_hour, day_end=day_end_hour,
        step_min=step_minutes,
    )
    out["note"] = (
        "supportive/tense labels follow the classical aspect-nature table; "
        "electional framing (waxing=begin, VoC=avoid commitments) is "
        "traditional rule, confidence 0.8"
    )
    out["provenance"] = geo["provenance"]
    return with_menu(
        out, domain="astro",
        known_inputs=[BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE, TARGET_DATE],
        completed=["electional-day"],
    )


def reverse_physiognomy_prompt(
    traits: list[str],
    subject_type: str,
    locale: str = "ru",
) -> dict[str, Any]:
    """Map character traits to face features (physiognomy KB in reverse).

    For a FICTIONAL character or the user's own self-description only —
    the KB ethics_note forbids reading third parties, and the reverse
    direction inherits that gate (subject_type must be "fictional" or
    "self", anything else raises).

    Returns matched KB entries (system, face features, verbatim reading,
    citation) per trait, unmatched traits, and a mechanical
    face_feature_seed string. The character-face skill composes the
    final RU/EN generation prompt + negative prompt from this seed.

    Args:
        traits: character-trait strings, ru or en (e.g. ["дисциплина",
            "стратег", "избирательность"]).
        subject_type: "fictional" or "self" — hard ethics gate.
        locale: "ru" (default) or "en" for feature/reading text.
    """
    out = _base("reverse-physiognomy", "physiognomy_dictionary", 0.6)
    out["computed"] = _reverse_physiognomy(traits, subject_type, locale)
    out["ethics_gate"] = "fictional_or_self_only"
    return with_menu(
        out, domain="astro",
        known_inputs=[TRAITS], completed=["character-face"], locale=locale,
    )
