"""Russian morphology in dream symbol matching + interpreter fallback.

Live testing showed a typical inflected Russian dream («лечу», «воду»,
«змею», «матери») losing 5 of 8 symbols to exact/prefix keyword matching,
and the interpreter returning BLANK text when the LLM provider chain has
no keys (the chain returns a stub with provider=None, which the parser
happily treated as an answer). These tests lock both fixes.
"""

from __future__ import annotations

import pytest

from backend.services.dreams import morphology
from backend.services.dreams.analyzer import DreamAnalyzer

# The session's live-demo dream: every symbol appears inflected.
INFLECTED_DREAM = (
    "Мне снилось, что я лечу над рекой возле дома моей матери. "
    "Вдруг начинается гроза, я падаю в тёмную воду и вижу змею. "
    "Я не боюсь, беру ключ со дна и просыпаюсь."
)


# ---------- Stemmer ----------------------------------------------------------


@pytest.mark.parametrize(
    "dict_form,inflected",
    [
        ("змея", "змею"),
        ("змея", "змеи"),
        ("вода", "воду"),
        ("вода", "водой"),
        ("река", "рекой"),
        ("падать", "падаю"),
        ("гроза", "грозой"),
        ("дом", "дома"),
    ],
)
def test_stem_unifies_case_forms(dict_form, inflected):
    assert morphology.stem(dict_form) == morphology.stem(inflected)


def test_stem_does_not_conflate_similar_words():
    """«водитель» (driver) must not collapse into «вода» (water)."""
    assert morphology.stem("водитель") != morphology.stem("вода")


def test_normalize_folds_yo():
    assert morphology.normalize("ПолЁт") == "полет"
    assert morphology.stem("полёт") == morphology.stem("полет")


def test_keyword_stems_skips_too_short_and_latin():
    stems = morphology.keyword_stems(["мать", "fly", "змея"])
    # "мать" stems to 2 chars → dropped as unsafe; latin ignored.
    assert stems == {morphology.stem("змея")}


# ---------- Analyzer: inflected Russian recall --------------------------------


def test_analyzer_finds_inflected_symbols():
    """The live-demo dream must yield the full symbol set, not just the
    three lucky exact matches (storm/house/key) it produced before."""
    analyzer = DreamAnalyzer()
    found = {s.symbol for s in analyzer._find_symbols(INFLECTED_DREAM, "ru")}
    expected = {
        "flying", "water", "snake", "mother", "falling",
        "storm", "house", "key",
    }
    missing = expected - found
    assert not missing, f"symbols lost to morphology: {missing}"


def test_analyzer_no_false_positive_from_similar_stems():
    """«Водитель вёл машину» is about driving — not the water symbol."""
    analyzer = DreamAnalyzer()
    found = {
        s.symbol
        for s in analyzer._find_symbols(
            "Водитель вёл машину по шоссе весь день", "ru"
        )
    }
    assert "water" not in found


def test_analyzer_english_matching_unchanged():
    analyzer = DreamAnalyzer()
    found = {
        s.symbol
        for s in analyzer._find_symbols(
            "I was flying over a river near my mother's house", "en"
        )
    }
    assert "flying" in found
    assert "house" in found


# ---------- Interpreter: no blank output without LLM keys ---------------------


@pytest.mark.asyncio
async def test_interpreter_falls_back_when_provider_chain_is_stub():
    """When the LLM chain answers with its stub (provider=None), the
    interpreter must produce the rule-based interpretation — summary,
    body and recommendations all non-empty — never blank text."""
    from backend.services.dreams.ai.interpreter import DreamInterpreter
    from backend.services.dreams.schemas import ContentAnalysis, EmotionType

    interpreter = DreamInterpreter()

    async def stub_generate(prompt, system_prompt=None, **kwargs):
        return "AI interpretation temporarily unavailable.", None

    interpreter.llm.generate = stub_generate  # type: ignore[assignment]

    analyzer = DreamAnalyzer()
    symbols = analyzer._find_symbols(INFLECTED_DREAM, "ru")

    summary, interpretation, recommendations = (
        await interpreter.generate_interpretation(
            dream_text=INFLECTED_DREAM,
            symbols=symbols,
            content=ContentAnalysis(),
            emotion=EmotionType.NEUTRAL,
            emotion_intensity=0.3,
            themes=["свобода"],
            archetypes=["liberation"],
            lunar_context=None,
            locale="ru",
        )
    )
    assert summary.strip(), "fallback summary must not be blank"
    assert interpretation.strip(), "fallback interpretation must not be blank"
    assert recommendations, "fallback must include recommendations"
    # It must be the rule-based text, not the provider stub.
    assert "temporarily unavailable" not in summary
    assert "Анализ символов" in interpretation
