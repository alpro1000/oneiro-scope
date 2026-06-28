"""Strategic Life Cycle Analyst — multi-layer decision-support primitives.

Implements the design from a peer review of OneiroScope: every insight
the system surfaces must declare WHICH layer it came from (astronomy is
not astrology; astrology is not psychology; symbolism is not fact),
carry a confidence rating, and never use deterministic language.

This module is the substrate for the new pivot: from "AI horoscope" to
"strategic life cycle analyst" — astrology is one analytical layer, not
the source of truth.
"""

from backend.services.strategic.layers import (
    Confidence,
    EvidenceMatrix,
    Insight,
    Layer,
    Source,
)
from backend.services.strategic.no_determinism import (
    DeterministicLanguageError,
    contains_determinism,
    soften,
)

__all__ = [
    "Confidence",
    "EvidenceMatrix",
    "Insight",
    "Layer",
    "Source",
    "DeterministicLanguageError",
    "contains_determinism",
    "soften",
]
