"""The template natal interpretation (LLM-absent fallback) must be clean.

Two shipped bugs this pins:
  * Russian output spliced in English keyword lists ("качествами Рака:
    nurturing, emotion") — the source keywords are English only.
  * Aspect lines took the FIRST CHARACTER of the planet name, so "Солнце
    opposition Луна" rendered as "- С opposition Л".
Both were visible in the very first live connector call.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic", reason="pydantic not installed")

from backend.services.astrology.interpreter import AstrologyInterpreter  # noqa: E402
from backend.services.astrology.schemas import (  # noqa: E402
    Aspect,
    AspectType,
    Planet,
    PlanetPosition,
    ZodiacSign,
)


def _planets():
    return [
        PlanetPosition(planet=Planet.SUN, sign=ZodiacSign.CANCER,
                       degree=99.8, sign_degree=9.8, retrograde=False),
        PlanetPosition(planet=Planet.MOON, sign=ZodiacSign.CAPRICORN,
                       degree=289.2, sign_degree=19.2, retrograde=False),
    ]


def _aspects():
    return [
        Aspect(planet1=Planet.SUN, planet2=Planet.MOON,
               aspect_type=AspectType.OPPOSITION, orb=9.4, applying=True),
        Aspect(planet1=Planet.SUN, planet2=Planet.MERCURY,
               aspect_type=AspectType.CONJUNCTION, orb=2.2, applying=True),
    ]


def test_russian_fallback_has_no_english_keyword_leak():
    out = AstrologyInterpreter()._template_interpret_natal(
        _planets(), None, _aspects(), "ru"
    )
    for leaked in ("nurturing", "emotion", "protection", "identity", "ego", "vitality"):
        assert leaked not in out, f"English keyword leaked into RU: {leaked}"


def test_russian_fallback_aspects_use_full_names_and_russian_relations():
    out = AstrologyInterpreter()._template_interpret_natal(
        _planets(), None, _aspects(), "ru"
    )
    # Full planet names, not the first-character truncation "- С ... Л".
    assert "Солнце" in out and "Луна" in out and "Меркурий" in out
    assert "\n- С " not in out and "\n- Л " not in out
    # Aspect relation words are Russian, not the raw enum value.
    assert "оппозиция" in out and "соединение" in out
    assert "opposition" not in out and "conjunction" not in out


def test_english_fallback_still_reads_naturally():
    out = AstrologyInterpreter()._template_interpret_natal(
        _planets(), None, _aspects(), "en"
    )
    assert "Sun in Cancer" in out
    assert "opposition" in out  # English keeps the standard aspect word
