"""Linguistic guard against deterministic prediction language.

The Strategic Life Cycle Analyst posture forbids statements like
"will happen", "случится", "произойдёт". Symbolic frameworks
(astrology, generated narrative) MUST be phrased as tendencies,
correlations, or conditional reflections — never as facts about the
future.

This module gives a fast deterministic check (regex) and a helper to
soften LLM output before user display.
"""

from __future__ import annotations

import re

# Surface-form patterns we reject in user-facing statements.
# Case-insensitive, word-boundary anchored where appropriate.
_BAD_PATTERNS_EN = [
    r"\bwill\b",
    r"\bshall\b",
    r"\bdefinitely\b",
    r"\bcertainly\b",
    r"\bguaranteed?\b",
    r"\bdestined\b",
    r"\bfated\b",
    r"\bmust happen\b",
    r"\bis going to\b",
]
# Russian variants — match common verb stems / phrasings.
_BAD_PATTERNS_RU = [
    r"\bбудет\b",
    r"\bбудут\b",
    r"\bпроизойдёт\b",
    r"\bпроизойдет\b",
    r"\bслучится\b",
    r"\bсудьба\b",
    r"\bобязательно\b",
    r"\bточно\b",  # "точно встретишь", "точно случится"
    r"\bпредрешено\b",
]

_RE_EN = re.compile("|".join(_BAD_PATTERNS_EN), re.IGNORECASE)
_RE_RU = re.compile("|".join(_BAD_PATTERNS_RU), re.IGNORECASE)


# Conditional / softening prefixes that legitimize otherwise-deterministic
# wording. If the sentence opens with one of these, the rule relaxes.
_HEDGE_PREFIXES_EN = (
    "if",
    "when",
    "after",
    "before",
    "should",
)
_HEDGE_PREFIXES_RU = (
    "если",
    "когда",
    "после того как",
    "при условии",
)

# Phrases that contain "will/будет" inside but are descriptive rather
# than predictive ("the period that will be useful") — allowlist of
# constructions we don't want to falsely flag.
_ALLOWED_PHRASES = (
    "this is traditionally associated with",
    "tends to",
    "this period traditionally",
    "if this model is useful",
    "может быть",
    "вероятно",
    "может проявиться",
    "традиционно связан с",
    "если эта модель полезна",
)


class DeterministicLanguageError(ValueError):
    """Raised when an Insight's statement uses forbidden language."""


def contains_determinism(text: str) -> list[str]:
    """Return the list of forbidden tokens found in `text`.

    Empty list = the text is acceptable. Non-empty = caller should
    rephrase. Does NOT raise — callers choose whether to raise.
    """
    lowered = text.lower()

    # Allow if a hedge prefix opens the sentence.
    stripped = lowered.lstrip()
    for pref in _HEDGE_PREFIXES_EN + _HEDGE_PREFIXES_RU:
        if stripped.startswith(pref + " ") or stripped.startswith(pref + ","):
            return []

    # Allow if the entire sentence is wrapped in an allowed phrase.
    for phrase in _ALLOWED_PHRASES:
        if phrase in lowered:
            return []

    hits = []
    hits.extend(m.group(0) for m in _RE_EN.finditer(text))
    hits.extend(m.group(0) for m in _RE_RU.finditer(text))
    return hits


# Replacement table for common deterministic verbs → tendency phrasings.
_SOFTENERS_EN = [
    (re.compile(r"\bwill\b", re.IGNORECASE), "tends to"),
    (re.compile(r"\bis going to\b", re.IGNORECASE), "is likely to"),
    (re.compile(r"\bdefinitely\b", re.IGNORECASE), "likely"),
    (re.compile(r"\bcertainly\b", re.IGNORECASE), "probably"),
    (re.compile(r"\bguaranteed\b", re.IGNORECASE), "favored"),
]
_SOFTENERS_RU = [
    (re.compile(r"\bбудет\b", re.IGNORECASE), "вероятно"),
    (re.compile(r"\bбудут\b", re.IGNORECASE), "вероятно будут"),
    (re.compile(r"\bпроизойдёт\b", re.IGNORECASE), "может произойти"),
    (re.compile(r"\bпроизойдет\b", re.IGNORECASE), "может произойти"),
    (re.compile(r"\bслучится\b", re.IGNORECASE), "может случиться"),
    (re.compile(r"\bточно\b", re.IGNORECASE), "вероятно"),
    (re.compile(r"\bобязательно\b", re.IGNORECASE), "скорее всего"),
]


def soften(text: str) -> str:
    """Rewrite deterministic language as tendency language.

    Use after LLM generation to clean up before display. Not perfect —
    some sentences need full rewriting; this is a defense-in-depth pass.
    """
    out = text
    for pat, repl in _SOFTENERS_EN + _SOFTENERS_RU:
        out = pat.sub(repl, out)
    return out
