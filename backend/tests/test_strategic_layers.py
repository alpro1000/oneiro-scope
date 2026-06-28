"""Tests for the Strategic Life Cycle Analyst substrate.

Covers `Layer`, `Source`, `Insight`, `EvidenceMatrix`, and the
no-determinism guard. Pure unit tests — no LLM, no chart computation.
"""

from __future__ import annotations

import pytest

from backend.services.strategic import (
    Confidence,
    DeterministicLanguageError,
    EvidenceMatrix,
    Insight,
    Layer,
    Source,
    contains_determinism,
    soften,
)
from backend.services.strategic.layers import insight


# ---------- no_determinism --------------------------------------------------


def test_contains_determinism_detects_english():
    assert contains_determinism("This will happen.")
    assert contains_determinism("It is going to be hard.")
    assert contains_determinism("Definitely a peak.")


def test_contains_determinism_detects_russian():
    assert contains_determinism("В сентябре будет кризис.")
    assert contains_determinism("Это точно случится.")
    assert contains_determinism("Произойдёт перемена.")


def test_contains_determinism_allows_hedged_sentences():
    # Conditional prefixes neutralize the rule.
    assert not contains_determinism("If you accept, it will lock in.")
    assert not contains_determinism("Если ты примешь, это будет важно.")
    # "When" also hedges.
    assert not contains_determinism("When the time comes, you will know.")


def test_contains_determinism_allows_traditional_phrasing():
    assert not contains_determinism(
        "This period is traditionally associated with reflection."
    )
    assert not contains_determinism(
        "Период традиционно связан с переоценкой."
    )
    assert not contains_determinism("Tends to bring change.")


def test_soften_replaces_english_will():
    assert "tends to" in soften("It will happen.")


def test_soften_replaces_russian_budet():
    assert "вероятно" in soften("Сентябрь будет тяжёлым.")


def test_soften_is_idempotent_for_clean_text():
    txt = "Период традиционно связан с переоценкой."
    assert soften(txt) == txt


# ---------- Layer / Source / Insight ----------------------------------------


def test_source_repr_includes_layer_kind_detail():
    s = Source(layer=Layer.ASTRONOMY, kind="transit", detail="Saturn □ Sun")
    assert "astronomy" in str(s)
    assert "transit" in str(s)
    assert "Saturn" in str(s)


def test_insight_rejects_deterministic_statement():
    # Pydantic v2 wraps the underlying DeterministicLanguageError in
    # ValidationError; we check the message survives.
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc:
        Insight(
            statement="September will be a crisis.",
            sources=[Source(layer=Layer.ASTROLOGY_SYMBOLIC, kind="square", detail="Saturn-Sun")],
            confidence=Confidence.LOW,
        )
    assert "deterministic" in str(exc.value).lower()
    assert "will" in str(exc.value)


def test_contains_determinism_helper_is_typed():
    # The plain-function path raises the right type, useful for
    # non-Pydantic call sites.
    bad = contains_determinism("This will definitely happen.")
    assert bad
    assert any("will" in b.lower() for b in bad)


def test_insight_accepts_softened_statement():
    i = Insight(
        statement="September tends to bring authority tests.",
        sources=[Source(layer=Layer.ASTROLOGY_SYMBOLIC, kind="square", detail="Saturn-Sun")],
        confidence=Confidence.LOW,
    )
    assert i.confidence == Confidence.LOW


def test_insight_layers_returns_unique_set():
    i = Insight(
        statement="Period of structural integration.",
        sources=[
            Source(layer=Layer.ASTRONOMY, kind="transit", detail="Sat □ Sun"),
            Source(layer=Layer.ASTRONOMY, kind="transit", detail="Jup ☌ Sat"),
            Source(layer=Layer.USER_CONTEXT, kind="event", detail="magistratura start"),
        ],
        confidence=Confidence.HIGH,
    )
    assert i.layers() == {Layer.ASTRONOMY, Layer.USER_CONTEXT}


# ---------- Confidence derivation ------------------------------------------


def test_confidence_high_when_objective_fact_present():
    sources = [
        Source(layer=Layer.OBJECTIVE_FACT, kind="event", detail="exam date"),
    ]
    assert EvidenceMatrix.compute_confidence(sources) == Confidence.HIGH


def test_confidence_high_when_two_hard_layers():
    sources = [
        Source(layer=Layer.ASTRONOMY, kind="transit", detail="Sat □ Sun"),
        Source(layer=Layer.USER_CONTEXT, kind="event", detail="job change"),
    ]
    assert EvidenceMatrix.compute_confidence(sources) == Confidence.HIGH


def test_confidence_high_when_hard_plus_statistical():
    sources = [
        Source(layer=Layer.ASTRONOMY, kind="transit", detail="Sat □ Sun"),
        Source(layer=Layer.AGE_PSYCHOLOGY, kind="stage", detail="Levinson midlife"),
    ]
    assert EvidenceMatrix.compute_confidence(sources) == Confidence.HIGH


def test_confidence_medium_when_single_hard_layer():
    sources = [
        Source(layer=Layer.ASTRONOMY, kind="transit", detail="Sat trine Sat"),
    ]
    assert EvidenceMatrix.compute_confidence(sources) == Confidence.MEDIUM


def test_confidence_medium_when_statistical_only():
    sources = [
        Source(layer=Layer.AGE_PSYCHOLOGY, kind="stage", detail="midlife"),
    ]
    assert EvidenceMatrix.compute_confidence(sources) == Confidence.MEDIUM


def test_confidence_low_when_symbolic_only():
    sources = [
        Source(layer=Layer.ASTROLOGY_SYMBOLIC, kind="aspect", detail="Sat □ Sun"),
    ]
    assert EvidenceMatrix.compute_confidence(sources) == Confidence.LOW


def test_confidence_low_when_llm_narrative_only():
    sources = [
        Source(layer=Layer.LLM_NARRATIVE, kind="reading", detail="auto-generated"),
    ]
    assert EvidenceMatrix.compute_confidence(sources) == Confidence.LOW


def test_confidence_color_codes():
    assert Confidence.HIGH.color == "🟢"
    assert Confidence.MEDIUM.color == "🟡"
    assert Confidence.LOW.color == "🔴"


# ---------- EvidenceMatrix --------------------------------------------------


def test_matrix_summary_counts():
    m = EvidenceMatrix(
        insights=[
            insight(
                "Statement A.",
                [Source(layer=Layer.OBJECTIVE_FACT, kind="x", detail="y")],
            ),
            insight(
                "Statement B.",
                [Source(layer=Layer.ASTROLOGY_SYMBOLIC, kind="x", detail="y")],
            ),
            insight(
                "Statement C.",
                [Source(layer=Layer.LLM_NARRATIVE, kind="x", detail="y")],
            ),
        ]
    )
    s = m.summary()
    assert s == {"high": 1, "medium": 0, "low": 2}


def test_matrix_sorted_puts_high_first():
    low = insight(
        "Low one.",
        [Source(layer=Layer.ASTROLOGY_SYMBOLIC, kind="x", detail="y")],
    )
    high = insight(
        "High one.",
        [Source(layer=Layer.OBJECTIVE_FACT, kind="x", detail="y")],
    )
    m = EvidenceMatrix(insights=[low, high])
    order = m.sorted()
    assert order[0].confidence == Confidence.HIGH
    assert order[1].confidence == Confidence.LOW


def test_insight_helper_auto_derives_confidence():
    i = insight(
        "Strong claim with two hard layers.",
        [
            Source(layer=Layer.ASTRONOMY, kind="t", detail="x"),
            Source(layer=Layer.USER_CONTEXT, kind="e", detail="y"),
        ],
    )
    assert i.confidence == Confidence.HIGH
