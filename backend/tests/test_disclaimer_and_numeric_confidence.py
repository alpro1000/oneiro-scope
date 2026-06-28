"""Tests for disclaimer enforcement + numeric confidence ladder."""

from __future__ import annotations

import pytest

from backend.services.strategic import (
    DISCLAIMER_EN,
    DISCLAIMER_RU,
    LAYER_CONFIDENCE,
    Layer,
    Source,
    ensure_disclaimer,
    has_disclaimer,
    numeric_confidence,
)


# ---------- Disclaimer -----------------------------------------------------


def test_has_disclaimer_detects_canonical_ru():
    text = "Какой-то текст. " + DISCLAIMER_RU
    assert has_disclaimer(text, "ru")


def test_has_disclaimer_detects_canonical_en():
    text = "Some text. " + DISCLAIMER_EN
    assert has_disclaimer(text, "en")


def test_has_disclaimer_returns_false_for_plain_text():
    assert not has_disclaimer("Просто текст без дисклеймера", "ru")
    assert not has_disclaimer("Plain text without disclaimer", "en")


def test_has_disclaimer_accepts_paraphrase():
    """LLM may phrase its own version — sentinel words satisfy the rule."""
    assert has_disclaimer(
        "Это не диагноз и не предсказание. Используйте для саморефлексии.",
        "ru",
    )
    assert has_disclaimer(
        "For reflection only — not medical advice.",
        "en",
    )


def test_ensure_disclaimer_appends_when_missing():
    plain = "Натальная карта показывает Sun в Раке."
    enriched = ensure_disclaimer(plain, "ru")
    assert has_disclaimer(enriched, "ru")
    assert "Sun в Раке" in enriched  # original preserved


def test_ensure_disclaimer_idempotent():
    text = "Какой-то текст. " + DISCLAIMER_RU
    assert ensure_disclaimer(text, "ru") == text


def test_ensure_disclaimer_picks_locale():
    plain = "Some content"
    en = ensure_disclaimer(plain, "en")
    assert "reflective" in en.lower() or "entertainment" in en.lower()


def test_ensure_disclaimer_falls_back_to_ru():
    """Unknown locale → uses Russian default."""
    enriched = ensure_disclaimer("текст", "zz")
    assert "рефлексивно" in enriched.lower()


# ---------- Numeric confidence ladder --------------------------------------


def test_layer_confidence_table_complete():
    expected_layers = {
        Layer.OBJECTIVE_FACT, Layer.ASTRONOMY, Layer.AGE_PSYCHOLOGY,
        Layer.CAREER_CYCLE, Layer.ECONOMICS, Layer.USER_CONTEXT,
        Layer.ASTROLOGY_SYMBOLIC, Layer.LLM_NARRATIVE,
    }
    assert set(LAYER_CONFIDENCE) == expected_layers


def test_confidence_ladder_values_match_scaffold():
    """The scaffold's 1.0/0.9/0.8/0.7 ladder is the contract."""
    assert LAYER_CONFIDENCE[Layer.OBJECTIVE_FACT] == 1.0
    assert LAYER_CONFIDENCE[Layer.ASTRONOMY] == 1.0
    assert LAYER_CONFIDENCE[Layer.AGE_PSYCHOLOGY] == 0.9
    assert LAYER_CONFIDENCE[Layer.ASTROLOGY_SYMBOLIC] == 0.8
    assert LAYER_CONFIDENCE[Layer.LLM_NARRATIVE] == 0.7


def test_numeric_confidence_picks_max_source():
    s = [
        Source(layer=Layer.LLM_NARRATIVE, kind="x", detail="y"),
        Source(layer=Layer.ASTRONOMY, kind="t", detail="z"),
    ]
    # Max(0.7, 1.0) = 1.0; only one hard layer → no bonus.
    assert numeric_confidence(s) == 1.0


def test_numeric_confidence_convergence_bonus():
    """Two hard layers → +0.05 bonus, capped at 1.0."""
    s = [
        Source(layer=Layer.ASTRONOMY, kind="t", detail="x"),
        Source(layer=Layer.USER_CONTEXT, kind="e", detail="y"),
    ]
    # max(1.0, 0.9) = 1.0, already capped.
    assert numeric_confidence(s) == 1.0


def test_numeric_confidence_llm_only_capped_at_0_7():
    s = [Source(layer=Layer.LLM_NARRATIVE, kind="x", detail="y")]
    assert numeric_confidence(s) == 0.7


def test_numeric_confidence_symbolic_only():
    s = [Source(layer=Layer.ASTROLOGY_SYMBOLIC, kind="x", detail="y")]
    assert numeric_confidence(s) == 0.8


def test_numeric_confidence_empty_sources():
    assert numeric_confidence([]) == 0.0


def test_numeric_confidence_two_user_contexts_count_as_convergence():
    """Two USER_CONTEXT sources (different facts) → bonus."""
    s = [
        Source(layer=Layer.USER_CONTEXT, kind="job", detail="berger"),
        Source(layer=Layer.USER_CONTEXT, kind="studies", detail="pardubice"),
    ]
    # max=0.9, hard_count=2, bonus=+0.05 → 0.95
    assert numeric_confidence(s) == 0.95
