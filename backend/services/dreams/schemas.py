"""
Dream Analysis Schemas

Pydantic models for dream analysis service based on
Hall/Van de Castle content analysis methodology.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class DreamCategory(str, Enum):
    """Hall/Van de Castle dream categories"""
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


class EmotionType(str, Enum):
    """Emotion types in dreams"""
    ANGER = "anger"
    APPREHENSION = "apprehension"
    SADNESS = "sadness"
    CONFUSION = "confusion"
    HAPPINESS = "happiness"
    NEUTRAL = "neutral"


class CharacterType(str, Enum):
    """Character types in dreams"""
    SELF = "self"
    KNOWN_MALE = "known_male"
    KNOWN_FEMALE = "known_female"
    UNKNOWN_MALE = "unknown_male"
    UNKNOWN_FEMALE = "unknown_female"
    ANIMAL = "animal"
    CREATURE = "creature"
    GROUP = "group"


class DreamSymbol(BaseModel):
    """Individual symbol found in dream"""
    symbol: str = Field(..., description="Symbol name")
    category: DreamCategory = Field(..., description="Hall/Van de Castle category")
    frequency: int = Field(default=1, description="Occurrence count")
    significance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Significance score 0-1"
    )
    interpretation_ru: str = Field(..., description="Russian interpretation")
    interpretation_en: str = Field(..., description="English interpretation")
    archetype: Optional[str] = Field(None, description="Jungian archetype if applicable")


class DreamSourceMetadata(BaseModel):
    """Metadata describing the origin of a dream record."""

    dataset: str = Field(..., description="Dataset name (SDDb, DreamBank, etc.)")
    source: Optional[str] = Field(None, description="Specific collection or cohort")
    gender: Optional[str] = Field(None, description="Reported gender")
    age: Optional[int] = Field(None, description="Age in years")
    date: Optional[date] = Field(None, description="When the dream was recorded")
    locale: Optional[str] = Field(None, description="Locale for text processing")
    sleep_stage: Optional[str] = Field(None, description="Sleep stage (REM/N1/N2/N3)")
    participant_id: Optional[str] = Field(None, description="Subject or participant identifier")


class DataProvenance(BaseModel):
    """Tracks lineage of ingested dream or physiological data."""

    dataset: str = Field(..., description="Dataset name")
    loader: str = Field(..., description="Connector or loader class name")
    uri: str = Field(..., description="Source URI or file path")
    ingested_at: datetime = Field(..., description="Timestamp when data was ingested")
    record_count: Optional[int] = Field(None, description="Number of rows or events ingested")


class DreamSourceRecord(BaseModel):
    """Standardized representation of a dream narrative from external datasets."""

    dream_text: str
    metadata: DreamSourceMetadata
    provenance: DataProvenance


class PhysiologicalEvent(BaseModel):
    """Physiological signal summary used for cross-indexing."""

    participant_id: Optional[str] = Field(None, description="Subject identifier")
    sleep_stage: Optional[str] = Field(None, description="Sleep stage for the event")
    channel_names: List[str] = Field(default_factory=list, description="Channels included in the recording")
    sampling_rate: float = Field(0.0, description="Sampling rate in Hz")
    start_time: Optional[datetime] = Field(None, description="Recording start time")
    duration_seconds: Optional[float] = Field(None, description="Recording duration in seconds")
    notes: Optional[str] = Field(None, description="Additional context about the event")
    provenance: Optional[DataProvenance] = Field(None, description="Lineage for this event")


class PhysiologicalCorrelation(BaseModel):
    """Correlation summary between archetypes and physiological events."""

    archetype: str = Field(..., description="Archetype identified in the dream")
    sleep_stages: List[str] = Field(default_factory=list, description="Stages co-occurring with the archetype")
    channel_summary: List[str] = Field(default_factory=list, description="Relevant channels or signals")
    evidence_count: int = Field(0, description="How many events support the link")
    rationale: str = Field(..., description="Text explanation of the link")


class DreamAnalysisRequest(BaseModel):
    """Request to analyze a dream"""
    dream_text: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Dream narrative text"
    )
    dream_date: Optional[date] = Field(
        None,
        description="Date when dream occurred (for lunar context)"
    )
    dreamer_gender: Optional[str] = Field(
        None,
        pattern="^(male|female|other)$",
        description="Dreamer's gender for norm comparison"
    )
    dreamer_age_group: Optional[str] = Field(
        None,
        pattern="^(child|teen|adult|senior)$",
        description="Age group for norm comparison"
    )
    locale: str = Field(
        default="ru",
        pattern="^(en|ru)$",
        description="Response language"
    )
    physiological_events: List[PhysiologicalEvent] = Field(
        default_factory=list,
        description="Optional physiological events aligned with the dream",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "dream_text": "I was flying over a beautiful city at night. The moon was full and bright. I felt free and happy.",
                    "dream_date": "2024-12-15",
                    "locale": "en"
                }
            ]
        }
    }


class ContentAnalysis(BaseModel):
    """Hall/Van de Castle content analysis results"""

    # Character counts
    male_characters: int = Field(default=0)
    female_characters: int = Field(default=0)
    animal_characters: int = Field(default=0)

    # Interaction types
    friendly_interactions: int = Field(default=0)
    aggressive_interactions: int = Field(default=0)
    sexual_interactions: int = Field(default=0)

    # Success/failure
    successes: int = Field(default=0)
    failures: int = Field(default=0)

    # Misfortunes
    misfortunes: int = Field(default=0)
    good_fortunes: int = Field(default=0)

    # Emotions
    positive_emotions: int = Field(default=0)
    negative_emotions: int = Field(default=0)

    # Derived ratios (compared to norms)
    male_female_ratio: Optional[float] = Field(None)
    aggression_friendliness_ratio: Optional[float] = Field(None)
    success_failure_ratio: Optional[float] = Field(None)


class LunarContext(BaseModel):
    """Lunar calendar context for the dream"""
    lunar_day: int = Field(..., ge=1, le=30)
    lunar_phase: str = Field(...)
    moon_sign: Optional[str] = Field(None)
    interpretation_ru: str = Field(...)
    interpretation_en: str = Field(...)


class DreamAnalysisResponse(BaseModel):
    """Complete dream analysis response"""
    status: str = Field(default="success")

    # Basic info
    dream_id: str = Field(..., description="Unique analysis ID")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    word_count: int = Field(..., description="Dream text word count")

    # Primary emotion
    primary_emotion: EmotionType = Field(...)
    emotion_intensity: float = Field(..., ge=0.0, le=1.0)

    # Symbols found
    symbols: List[DreamSymbol] = Field(default_factory=list)

    # Content analysis
    content_analysis: ContentAnalysis = Field(...)

    # Lunar context (if date provided)
    lunar_context: Optional[LunarContext] = Field(None)

    # AI interpretation
    summary: str = Field(..., description="Brief summary")
    interpretation: str = Field(..., description="Detailed interpretation")

    # Psychological insights
    themes: List[str] = Field(default_factory=list, description="Main themes")
    archetypes: List[str] = Field(default_factory=list, description="Jungian archetypes")

    physiological_correlations: List[PhysiologicalCorrelation] = Field(
        default_factory=list,
        description="Links between dream archetypes and physiological markers",
    )
    source_provenance: List[DataProvenance] = Field(
        default_factory=list,
        description="Lineage for any external datasets used in the analysis",
    )

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)

    # Methodology note
    methodology: str = Field(
        default="Hall/Van de Castle content analysis + DreamBank corpus comparison"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "dream_id": "dream_abc123",
                    "word_count": 45,
                    "primary_emotion": "happiness",
                    "emotion_intensity": 0.8,
                    "summary": "A liberating flying dream indicating desire for freedom",
                    "interpretation": "Flying dreams often represent..."
                }
            ]
        }
    }
