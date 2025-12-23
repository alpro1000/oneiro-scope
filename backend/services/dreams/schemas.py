"""Lightweight dream analysis schemas.

These schemas are simplified placeholders to keep test environments from
tripping over heavy recursive Pydantic configuration. They retain the key
interfaces used by imports elsewhere in the codebase without pulling in
complex nested models.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, List
from datetime import date, datetime

from pydantic import BaseModel, Field


class DreamCategory(str, Enum):
    """Hall/Van de Castle dream content categories."""

    CHARACTERS = "characters"
    SOCIAL_INTERACTIONS = "social_interactions"
    ACTIVITIES = "activities"
    STRIVING = "striving"
    MISFORTUNES = "misfortunes"
    GOOD_FORTUNES = "good_fortunes"
    EMOTIONS = "emotions"
    SETTINGS = "settings"
    OBJECTS = "objects"
    DESCRIPTIVE_ELEMENTS = "descriptive_elements"


class CharacterType(str, Enum):
    """Simplified character taxonomy for analysis ratios."""

    MALE = "male"
    FEMALE = "female"
    ANIMAL = "animal"


class DreamSymbol(BaseModel):
    """Minimal representation of a dream symbol."""

    symbol: str = Field(..., description="Symbol name")
    category: DreamCategory = Field(DreamCategory.OBJECTS, description="Symbol category")
    frequency: int = Field(0, description="How many times the symbol appeared")
    significance: float = Field(0.0, description="Relative significance of the symbol")
    interpretation_ru: Optional[str] = Field(None, description="Russian interpretation")
    interpretation_en: Optional[str] = Field(None, description="English interpretation")
    archetype: Optional[str] = Field(None, description="Linked Jungian archetype")


class EmotionType(str, Enum):
    """Simplified emotion classification."""

    HAPPINESS = "happiness"
    SADNESS = "sadness"
    FEAR = "fear"
    ANGER = "anger"
    APPREHENSION = "apprehension"
    CONFUSION = "confusion"
    NEUTRAL = "neutral"


class ContentAnalysis(BaseModel):
    """Lightweight content analysis summary."""

    male_characters: int = 0
    female_characters: int = 0
    animal_characters: int = 0
    friendly_interactions: int = 0
    aggressive_interactions: int = 0
    sexual_interactions: int = 0
    successes: int = 0
    failures: int = 0
    misfortunes: int = 0
    good_fortunes: int = 0
    positive_emotions: int = 0
    negative_emotions: int = 0
    male_female_ratio: Optional[float] = None
    aggression_friendliness_ratio: Optional[float] = None
    success_failure_ratio: Optional[float] = None


class LunarContext(BaseModel):
    """Minimal lunar context used by interpreter stubs."""

    lunar_day: int = 1
    lunar_phase: str = "new"
    moon_sign: Optional[str] = None
    interpretation_ru: Optional[str] = None
    interpretation_en: Optional[str] = None


class PhysiologicalEvent(BaseModel):
    """Physiological recording snippet aligned with a dream event."""

    participant_id: Optional[str] = None
    sleep_stage: Optional[str] = None
    channel_names: List[str] = Field(default_factory=list)
    sampling_rate: float = 0.0
    start_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    notes: Optional[str] = None
    provenance: Optional["DataProvenance"] = None


class PhysiologicalCorrelation(BaseModel):
    """Lightweight correlation summary between physiology and archetypes."""

    archetype: str
    sleep_stages: List[str] = Field(default_factory=list)
    channel_summary: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    rationale: Optional[str] = None


class DataProvenance(BaseModel):
    """Provenance metadata for ingested dream or physiology records."""

    dataset: str
    loader: str
    uri: str
    record_count: int
    ingested_at: datetime


class DreamSourceMetadata(BaseModel):
    """Metadata describing the origin of a dream narrative."""

    dataset: str
    source: str
    gender: Optional[str] = None
    age: Optional[str] = None
    date: Optional[str] = None
    locale: str = "en"
    sleep_stage: Optional[str] = None
    participant_id: Optional[str] = None


class DreamSourceRecord(BaseModel):
    """A dream narrative and its provenance."""

    dream_text: str
    metadata: DreamSourceMetadata
    provenance: DataProvenance


class DreamAnalysisRequest(BaseModel):
    """Request payload for dream analysis."""

    dream_text: str = Field(..., min_length=1, description="Dream narrative text")
    dream_date: Optional[date] = Field(None, description="Date of the dream if known")
    locale: str = Field(default="ru", description="Response language")
    dreamer_gender: Optional[str] = Field(None, description="Self-reported gender")
    dreamer_age_group: Optional[str] = Field(None, description="Age group")
    physiological_events: Optional[List[PhysiologicalEvent]] = Field(
        None, description="Physiology aligned to the dream",
    )


class NormDeviation(BaseModel):
    """Single indicator deviation from Hall/Van de Castle norms"""
    indicator: str = Field(..., description="Norm indicator name")
    user_value: float = Field(..., description="User's dream value")
    norm_value: float = Field(..., description="Expected norm value")
    deviation: float = Field(..., description="Deviation in percentage points")
    significance: str = Field(..., description="significant/moderate/normal")
    description_ru: str = Field(..., description="Russian description")
    description_en: str = Field(..., description="English description")


class NormComparisonResult(BaseModel):
    """Comparison of dream content to Hall/Van de Castle norms"""
    gender_used: str = Field(..., description="Gender norms used (male/female)")
    overall_typicality: float = Field(
        ...,
        ge=0,
        le=100,
        description="How typical the dream is (0-100%)"
    )
    deviations: List[NormDeviation] = Field(
        default_factory=list,
        description="List of deviations from norms"
    )
    notable_findings_ru: List[str] = Field(
        default_factory=list,
        description="Notable findings in Russian"
    )
    notable_findings_en: List[str] = Field(
        default_factory=list,
        description="Notable findings in English"
    )


class DreamAnalysisResponse(BaseModel):
    """Simplified analysis response used in tests."""

    status: str = Field(default="success")
    dream_id: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    word_count: int = 0
    primary_emotion: Optional[EmotionType] = None
    emotion_intensity: float = 0.0
    symbols: List[DreamSymbol] = Field(default_factory=list)
    content_analysis: Optional[ContentAnalysis] = None
    lunar_context: Optional[LunarContext] = None

    # Norm comparison (Hall/Van de Castle)
    norm_comparison: Optional[NormComparisonResult] = Field(
        None,
        description="Comparison to Hall/Van de Castle norms based on dreamer gender"
    )

    summary: Optional[str] = None
    interpretation: Optional[str] = None
    themes: List[str] = Field(default_factory=list)
    archetypes: List[str] = Field(default_factory=list)
    physiological_correlations: List[PhysiologicalCorrelation] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    methodology: str = Field(
        default="Hall/Van de Castle content analysis with Jungian archetypes and lunar context",
        description="Short description of the analysis pipeline",
    )


__all__ = [
    "DreamCategory",
    "CharacterType",
    "DreamSymbol",
    "EmotionType",
    "ContentAnalysis",
    "LunarContext",
    "PhysiologicalEvent",
    "PhysiologicalCorrelation",
    "DataProvenance",
    "DreamSourceMetadata",
    "DreamSourceRecord",
    "DreamAnalysisRequest",
    "DreamAnalysisResponse",
]
