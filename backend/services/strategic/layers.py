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

    @property
    def numeric(self) -> float:
        """Numeric confidence on the 0-1 ladder (per scaffold suggestion).

        Maps:
        - HIGH = 0.9 (default cited classical rule)  → upgraded to 1.0 by
                source mix when objective_fact is present
        - MEDIUM = 0.8 (symbol dictionary / single hard layer)
        - LOW = 0.7 (LLM synthesis only)
        """
        return {"high": 0.9, "medium": 0.8, "low": 0.7}[self.value]


# Per-source-layer numeric confidence ladder (scaffold §3 idea).
# These are the BASELINE contributions; combined confidence may
# exceed 0.9 when objective facts or convergence are present.
LAYER_CONFIDENCE: dict["Layer", float] = {}  # filled at bottom — Layer defined above


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


# --- THE confidence ladder ----------------------------------------------------
# This table is the single source of truth. CLAUDE.md quotes it, and
# `test_confidence_ladder_docs.py` fails when the two disagree — the two had
# already drifted apart once, which is how a project whose whole pitch is
# "every claim carries its confidence" ended up documenting a ladder it was
# not running.
#
# Four rungs are the ladder proper — how a claim was ARRIVED at:
#
#   1.00  computed or verified   — an ephemeris result, or a fact checked
#                                  against a record. Reproducible.
#   0.90  cited rule / study     — named source, someone else's peer review.
#   0.80  dictionary lookup      — a tradition's own table of meanings.
#   0.70  generated synthesis    — the model joining the above into prose.
#
# The remaining entries are the layers this codebase actually has, each placed
# on that ladder rather than given a rung of its own. Where a layer sits
# between rungs it is written down as such, with the reason:
#
#   0.85  statistics without a per-claim citation — an industry cycle or a
#         macro series is real evidence, but weaker than a study we can name.
#
# NOTE on USER_CONTEXT. The comment here used to say 0.6 while the code said
# 0.9. 0.9 is right and the comment was the error: what the user tells us
# about their own life is strong evidence ABOUT THAT USER — below 1.0 only
# because it is self-reported rather than verified. "Not generalisable" is a
# statement about scope, not about confidence, and conflating the two is what
# produced the discrepancy.
LAYER_CONFIDENCE.update({
    Layer.OBJECTIVE_FACT: 1.0,        # verified life event / bank record
    Layer.ASTRONOMY: 1.0,             # Swiss Ephemeris computation
    Layer.AGE_PSYCHOLOGY: 0.9,        # peer-reviewed (Erikson, Levinson, H/VdC)
    Layer.USER_CONTEXT: 0.9,          # self-reported, about the reporter
    Layer.CAREER_CYCLE: 0.85,         # industry statistics, uncited per claim
    Layer.ECONOMICS: 0.85,            # macro data, uncited per claim
    Layer.ASTROLOGY_SYMBOLIC: 0.8,    # symbol dictionary / classical rule
    Layer.LLM_NARRATIVE: 0.7,         # generated synthesis
})

#: The four rungs, as documentation quotes them. Keyed by the phrase CLAUDE.md
#: uses so the doc-sync test can match on meaning rather than on wording.
LADDER_RUNGS: dict[str, float] = {
    "ephemeris/calc": 1.0,
    "cited classical rule": 0.9,
    "symbol dictionary": 0.8,
    "LLM synthesis": 0.7,
}


# --- WP-13: the same ladder, said in words -----------------------------------
#
# `"confidence": 0.7` is read by everyone — a model, a user, a directory
# reviewer — as "70% likely to be true". It never meant that. It means "this
# claim came from the model-synthesis tier", which is a statement about
# PROVENANCE, not about probability. On an astrology server that misreading is
# not cosmetic: a number that looks like a likelihood turns a tradition's
# reading into a prediction with odds attached, which is exactly the claim the
# whole product refuses to make.
#
# So each claim now also carries the tier by NAME. The number stays, unchanged
# and in place — this is an additive migration, and nothing that reads
# `confidence` today has to change. Renaming it outright would break every
# client at once, and (the reason it is happening NOW rather than later)
# publishing to a directory freezes field names: after the listing, changing
# them costs a re-review cycle on OpenAI's side.
class RuleSourceTier(str, Enum):
    """HOW a claim was arrived at. Not how likely it is to be true."""

    #: Ephemeris result or a fact checked against a record. Reproducible.
    COMPUTED = "computed"
    #: A named source — a classical rule, or someone else's peer review.
    CITED_RULE = "cited_rule"
    #: Statistics with no per-claim citation: real evidence, weaker than a
    #: study we can name. The one tier that sits between rungs, deliberately.
    STATISTICAL = "statistical"
    #: A tradition's own table of meanings.
    SYMBOL_DICTIONARY = "symbol_dictionary"
    #: The model joining the above into prose.
    MODEL_SYNTHESIS = "model_synthesis"
    #: A tradition with no empirical validation at all — physiognomy. Below
    #: the ladder's lowest rung on purpose: weaker than a symbol dictionary,
    #: and the reading itself says so (Todorov 2017).
    UNVALIDATED_TRADITION = "unvalidated_tradition"


#: Tier → the number it has always carried. The single place the two
#: vocabularies meet; everything else derives from here.
TIER_CONFIDENCE: dict[RuleSourceTier, float] = {
    RuleSourceTier.COMPUTED: 1.0,
    RuleSourceTier.CITED_RULE: 0.9,
    RuleSourceTier.STATISTICAL: 0.85,
    RuleSourceTier.SYMBOL_DICTIONARY: 0.8,
    RuleSourceTier.MODEL_SYNTHESIS: 0.7,
    RuleSourceTier.UNVALIDATED_TRADITION: 0.6,
}

#: Layer → tier. Where a caller knows the layer, this is the authoritative
#: route: the tier is a property of WHERE a claim came from, and the number is
#: a consequence of the tier rather than the other way round.
LAYER_TIER: dict["Layer", RuleSourceTier] = {
    Layer.OBJECTIVE_FACT: RuleSourceTier.COMPUTED,
    Layer.ASTRONOMY: RuleSourceTier.COMPUTED,
    Layer.AGE_PSYCHOLOGY: RuleSourceTier.CITED_RULE,
    Layer.USER_CONTEXT: RuleSourceTier.CITED_RULE,
    Layer.CAREER_CYCLE: RuleSourceTier.STATISTICAL,
    Layer.ECONOMICS: RuleSourceTier.STATISTICAL,
    Layer.ASTROLOGY_SYMBOLIC: RuleSourceTier.SYMBOL_DICTIONARY,
    Layer.LLM_NARRATIVE: RuleSourceTier.MODEL_SYNTHESIS,
}

_CONFIDENCE_TIER: dict[float, RuleSourceTier] = {
    v: k for k, v in TIER_CONFIDENCE.items()
}


def tier_for_confidence(value: float) -> RuleSourceTier:
    """Name the tier a bare number belongs to.

    For the call sites that carry a hardcoded confidence and no layer. An
    unrecognised value RAISES rather than guessing a nearby tier
    (conventions.md §12): a claim labelled with the wrong provenance is worse
    than one labelled with none, and the combined values `numeric_confidence`
    produces (0.95 from converging hard layers) are deliberately NOT in this
    table — a combined score is not a tier, and forcing it into one would
    invent a source the claim does not have. Route those through
    `tier_for_sources` instead.
    """
    tier = _CONFIDENCE_TIER.get(round(float(value), 4))
    if tier is None:
        raise ValueError(
            f"confidence {value!r} is not a tier on the ladder "
            f"{sorted(_CONFIDENCE_TIER)} — pass the layer instead of a number, "
            f"or add the tier deliberately"
        )
    return tier


def tier_for_sources(sources: list["Source"]) -> RuleSourceTier:
    """The tier of the strongest source behind a claim.

    A claim is only as well-founded as its best evidence, and combining
    several weak sources does not produce a strong one — which is why this
    takes the max rather than an average.
    """
    if not sources:
        return RuleSourceTier.MODEL_SYNTHESIS
    return max(
        (LAYER_TIER[s.layer] for s in sources if s.layer in LAYER_TIER),
        key=lambda t: TIER_CONFIDENCE[t],
        default=RuleSourceTier.MODEL_SYNTHESIS,
    )


def numeric_confidence(sources: list[Source]) -> float:
    """Combine numeric per-source confidences using the scaffold rule:

    - Start from the highest-confidence source in the mix.
    - Convergence bonus: +0.05 per additional hard layer (capped at 1.0).
    - Penalty: if ONLY LLM_NARRATIVE present, cap at 0.7.
    """
    if not sources:
        return 0.0
    vals = [LAYER_CONFIDENCE.get(s.layer, 0.7) for s in sources]
    base = max(vals)
    hard_count = sum(
        1 for s in sources
        if s.layer in (Layer.OBJECTIVE_FACT, Layer.ASTRONOMY, Layer.USER_CONTEXT)
    )
    if hard_count >= 2:
        base = min(1.0, base + 0.05 * (hard_count - 1))
    # LLM-only floor.
    if {s.layer for s in sources} == {Layer.LLM_NARRATIVE}:
        base = min(base, 0.7)
    return round(base, 2)
