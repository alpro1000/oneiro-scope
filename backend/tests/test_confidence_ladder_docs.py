"""The documented confidence ladder must be the one the code runs.

"Every claim carries its confidence" is the project's central promise, so a
gap between the ladder in `CLAUDE.md` and the one in `LAYER_CONFIDENCE` is not
a documentation nit — it means the number a user is shown was justified by a
rule nobody is enforcing. The two had in fact drifted: the docs stated four
rungs (1.0 / 0.9 / 0.8 / 0.7), the code carried eight entries including two at
0.85 that appear nowhere in the docs, and a comment inside the code itself
claimed USER_CONTEXT was 0.6 while the code set it to 0.9.

The fix is not to make them identical — the code legitimately has more layers
than the ladder has rungs. It is to make every layer sit ON a rung, or sit
between two rungs for a written reason, and to let neither side move alone.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.services.strategic.layers import (
    LADDER_RUNGS,
    LAYER_CONFIDENCE,
    Confidence,
    Layer,
)

CLAUDE_MD = Path(__file__).resolve().parents[2] / "CLAUDE.md"


def test_the_docs_state_every_rung_at_the_value_the_code_uses():
    """Parse the ladder out of CLAUDE.md and compare it to the code.

    Matching on the phrase rather than on layout: the file states the ladder
    twice, in a TL;DR and in the principles section, and both are wrapped at
    different widths.
    """
    # Normalise the wrapping so "cited classical rule =\n> 0.9" still matches.
    text = re.sub(r"\s*\n>?\s*", " ", CLAUDE_MD.read_text(encoding="utf-8"))

    for phrase, expected in LADDER_RUNGS.items():
        # `[0-9.]+` would swallow the sentence-ending full stop in "= 0.7."
        found = re.findall(rf"{re.escape(phrase)}\s*=\s*(\d+(?:\.\d+)?)", text)
        assert found, f"CLAUDE.md no longer states the rung '{phrase}'"
        for value in found:
            assert float(value) == expected, (
                f"CLAUDE.md says {phrase} = {value}, the code says {expected}"
            )


def test_every_layer_sits_on_a_rung_or_between_two():
    """No layer may invent a confidence outside the ladder's range."""
    rungs = sorted(LADDER_RUNGS.values())
    for layer, value in LAYER_CONFIDENCE.items():
        assert rungs[0] <= value <= rungs[-1], (
            f"{layer} has confidence {value}, outside the ladder {rungs}"
        )


def test_layers_between_rungs_are_deliberate_and_few():
    """0.85 is allowed, but only where the code says why.

    A layer that lands between rungs is a judgement call, and judgement calls
    should be rare and written down. If this list grows, the ladder needs
    another rung rather than another exception.
    """
    off_rung = {
        layer: value for layer, value in LAYER_CONFIDENCE.items()
        if value not in set(LADDER_RUNGS.values())
    }
    assert off_rung == {Layer.CAREER_CYCLE: 0.85, Layer.ECONOMICS: 0.85}, off_rung

    source = Path(__file__).resolve().parents[1] / "services" / "strategic" / "layers.py"
    body = source.read_text(encoding="utf-8")
    assert "0.85" in body and "uncited per claim" in body, (
        "the between-rung values must carry their reason in the code"
    )


def test_no_layer_is_left_without_a_confidence():
    """A layer the table forgets silently falls back to 0.7 in
    `numeric_confidence` — i.e. an astronomy result would be scored as if the
    model had made it up."""
    missing = [layer for layer in Layer if layer not in LAYER_CONFIDENCE]
    assert not missing, f"layers with no confidence: {missing}"


def test_the_coarse_labels_agree_with_the_numeric_ladder():
    """`Confidence.numeric` and `LAYER_CONFIDENCE` are two ways to say the
    same thing, and they are consulted by different call sites."""
    assert Confidence.HIGH.numeric == LADDER_RUNGS["cited classical rule"]
    assert Confidence.MEDIUM.numeric == LADDER_RUNGS["symbol dictionary"]
    assert Confidence.LOW.numeric == LADDER_RUNGS["LLM synthesis"]


@pytest.mark.parametrize(
    "layer,expected",
    [
        (Layer.ASTRONOMY, 1.0),
        (Layer.OBJECTIVE_FACT, 1.0),
        (Layer.ASTROLOGY_SYMBOLIC, 0.8),
        (Layer.LLM_NARRATIVE, 0.7),
        # The one that was contradicted by its own comment.
        (Layer.USER_CONTEXT, 0.9),
    ],
)
def test_the_load_bearing_values_are_pinned(layer, expected):
    assert LAYER_CONFIDENCE[layer] == expected


def test_computation_is_never_scored_below_interpretation():
    """The ordering IS the principle: a higher-confidence source is never
    overwritten by a lower one."""
    assert LAYER_CONFIDENCE[Layer.ASTRONOMY] > LAYER_CONFIDENCE[Layer.ASTROLOGY_SYMBOLIC]
    assert LAYER_CONFIDENCE[Layer.ASTROLOGY_SYMBOLIC] > LAYER_CONFIDENCE[Layer.LLM_NARRATIVE]
