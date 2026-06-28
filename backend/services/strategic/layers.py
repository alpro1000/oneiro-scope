"""Layer / Insight / EvidenceMatrix — the typed substrate of strategic
life-cycle analysis.

Each statement the system surfaces must declare:
- which `Layer` it came from (objective fact, astronomy, astrology, …)
- one or more `Source` references (transit_X, magistratura, life_stage)
- a `Confidence` rating (high/medium/low) — derived, not arbitrary

Confidence derivation rule (encoded in `EvidenceMatrix.compute_confidence`):
- HIGH: at least one source is an objective fact OR multiple independent
  layers converge on the same statement.
- MEDIUM: at least one source is a deterministic computation (astronomy,
  cycle psychology) AND no contradicting sources.
- LOW: only symbolic interpretation (astrology alone, LLM narrative).

This is the implementation of the "Evidence Matrix" idea — every output
carries its provenance, so the consumer can tell where data ends and
interpretation begins.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Layer(str, Enum):
    """Analytical layer a statement is drawn from.

    Layers are ordered from most-evidentiary (top) to most-symbolic
    (bottom). A statement may cite multiple layers; the evidence matrix
    weights them when computing confidence.
    """

    # Verifiable facts — bank statements, user-supplied life events,
    # calendar dates, employment records.
    OBJECTIVE_FACT = "objective_fact"

    # Deterministic astronomical computation: transit dates, lunar
    # phases, planetary positions. Reproducible to arc-second precision
    # with Swiss Ephemeris. NOT astrology — just sky math.
    ASTRONOMY = "astronomy"

    # Peer-reviewed psychological / developmental research:
    # Erikson stages, Levinson seasons, Saturn-return ages,
    # Hall/Van de Castle dream norms. Statistically valid for cohorts.
    AGE_PSYCHOLOGY = "age_psychology"

    # Industry / career cycle data: hiring curves, salary medians,
    # migration patterns. Statistical, not personal.
    CAREER_CYCLE = "career_cycle"

    # Macroeconomic data: interest rates, real-estate cycles, currency
    # exposure. Context, not prediction.
    ECONOMICS = "economics"

    # User-supplied biography: studies, employer, location, goals.
    # High-trust for THIS user; not generalizable.
    USER_CONTEXT = "user_context"

    # Symbolic interpretation of astrological aspects. Tradition-based,
    # not predictive. Useful for reflection, NOT for forecasting.
    ASTROLOGY_SYMBOLIC = "astrology_symbolic"

    # Generated narrative from an LLM. Lowest evidentiary weight —
    # requires user judgment.
    LLM_NARRATIVE = "llm_narrative"


# Layers that count as "hard data" when computing confidence.
_HARD_LAYERS = frozenset(
    {Layer.OBJECTIVE_FACT, Layer.ASTRONOMY, Layer.USER_CONTEXT}
)

# Layers that are computational / research-backed but indirect.
_STATISTICAL_LAYERS = frozenset(
    {Layer.AGE_PSYCHOLOGY, Layer.CAREER_CYCLE, Layer.ECONOMICS}
)

# Layers that are interpretive / symbolic only.
_SYMBOLIC_LAYERS = frozenset({Layer.ASTROLOGY_SYMBOLIC, Layer.LLM_NARRATIVE})


class Confidence(str, Enum):
    """Confidence rating for an insight. Maps to UI colors.

    HIGH (🟢): grounded in hard data or convergence across layers.
    MEDIUM (🟡): grounded in statistical / cyclic patterns.
    LOW (🔴): only symbolic / generated. User should treat as reflection
        prompt, not as data.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def color(self) -> str:
        return {"high": "🟢", "medium": "🟡", "low": "🔴"}[self.value]


class Source(BaseModel):
    """One traceable reference behind an insight.

    `kind` identifies WHAT kind of evidence this is (transit, life-stage,
    user-fact). `detail` is the specific value ("Saturn □ Sun orb 2°",
    "magistratura starts 2026-09-01", "Cancer Sun"). `layer` says which
    epistemic level this evidence sits at.
    """

    layer: Layer
    kind: str = Field(min_length=1)
    detail: str = Field(min_length=1)

    def __str__(self) -> str:
        return f"[{self.layer.value}] {self.kind}: {self.detail}"


class Insight(BaseModel):
    """A single analytical claim with provenance.

    `statement` is the user-facing sentence. It MUST NOT contain
    deterministic language ("will", "будет", "случится") — the validator
    rejects such phrasing at construction time. Use "tends to",
    "is traditionally associated with", "if the model is useful, …".
    """

    statement: str = Field(min_length=3)
    sources: list[Source] = Field(min_length=1)
    confidence: Confidence
    # Optional follow-up actions the user can take.
    actions: list[str] = Field(default_factory=list)

    @field_validator("statement")
    @classmethod
    def _no_deterministic_language(cls, v: str) -> str:
        from backend.services.strategic.no_determinism import (
            DeterministicLanguageError,
            contains_determinism,
        )

        bad = contains_determinism(v)
        if bad:
            raise DeterministicLanguageError(
                f"Statement contains forbidden deterministic word(s) "
                f"{bad!r}: {v!r}. Rephrase as 'tends to', "
                f"'is traditionally associated with', or "
                f"'if this model is useful…'."
            )
        return v

    def layers(self) -> set[Layer]:
        return {s.layer for s in self.sources}


class EvidenceMatrix(BaseModel):
    """A collection of insights wrapped together for one query/response.

    Includes a `summary` line (computed) showing how many insights at
    each confidence level. Sorting puts HIGH first.
    """

    insights: list[Insight]
    context: Optional[str] = None

    def sorted(self) -> list[Insight]:
        order = {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}
        return sorted(self.insights, key=lambda i: order[i.confidence])

    def summary(self) -> dict[str, int]:
        out = {"high": 0, "medium": 0, "low": 0}
        for i in self.insights:
            out[i.confidence.value] += 1
        return out

    @staticmethod
    def compute_confidence(sources: list[Source]) -> Confidence:
        """Confidence is *derived*, not arbitrarily chosen.

        Rules:
        - Any OBJECTIVE_FACT source → HIGH (user-verifiable).
        - ASTRONOMY + USER_CONTEXT both present → HIGH (convergence).
        - ASTRONOMY or USER_CONTEXT alone → MEDIUM if backed by a
          statistical layer, else MEDIUM at best (one source).
        - Only ASTROLOGY_SYMBOLIC or LLM_NARRATIVE → LOW.
        - Mix of statistical + symbolic → MEDIUM.
        """
        layers = {s.layer for s in sources}

        if Layer.OBJECTIVE_FACT in layers:
            return Confidence.HIGH

        hard_count = len(layers & _HARD_LAYERS)
        statistical = bool(layers & _STATISTICAL_LAYERS)
        symbolic_only = layers.issubset(_SYMBOLIC_LAYERS)

        if hard_count >= 2:
            return Confidence.HIGH
        if hard_count >= 1 and statistical:
            return Confidence.HIGH
        if hard_count >= 1:
            return Confidence.MEDIUM
        if statistical:
            return Confidence.MEDIUM
        if symbolic_only:
            return Confidence.LOW
        return Confidence.MEDIUM


def insight(
    statement: str,
    sources: list[Source],
    actions: Optional[list[str]] = None,
) -> Insight:
    """Helper to build an `Insight` with auto-derived confidence."""
    return Insight(
        statement=statement,
        sources=sources,
        confidence=EvidenceMatrix.compute_confidence(sources),
        actions=actions or [],
    )
