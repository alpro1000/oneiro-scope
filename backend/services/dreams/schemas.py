"""Lightweight dream analysis schemas.

These schemas are simplified placeholders to keep test environments from
tripping over heavy recursive Pydantic configuration. They retain the key
interfaces used by imports elsewhere in the codebase without pulling in
complex nested models.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from datetime import date

from pydantic import BaseModel, Field


class DreamCategory(str, Enum):
    """Basic dream category taxonomy."""

    CHARACTERS = "characters"
    EMOTIONS = "emotions"
    SETTINGS = "settings"
    OBJECTS = "objects"


class DreamSymbol(BaseModel):
    """Minimal representation of a dream symbol."""

    symbol: str = Field(..., description="Symbol name")
    category: DreamCategory = Field(DreamCategory.OBJECTS, description="Symbol category")


class EmotionType(str, Enum):
    """Simplified emotion classification."""

    HAPPINESS = "happiness"
    SADNESS = "sadness"
    FEAR = "fear"
    NEUTRAL = "neutral"


class ContentAnalysis(BaseModel):
    """Lightweight content analysis summary."""

    positive_emotions: int = 0
    negative_emotions: int = 0
    themes: list[str] = Field(default_factory=list)


class LunarContext(BaseModel):
    """Minimal lunar context used by interpreter stubs."""

    lunar_day: int = 1
    lunar_phase: str = "new"
    interpretation_ru: Optional[str] = None
    interpretation_en: Optional[str] = None


class DreamAnalysisRequest(BaseModel):
    """Request payload for dream analysis."""

    dream_text: str = Field(..., min_length=1, description="Dream narrative text")
    dream_date: Optional[date] = Field(None, description="Date of the dream if known")
    locale: str = Field(default="ru", description="Response language")


class DreamAnalysisResponse(BaseModel):
    """Simplified analysis response used in tests."""

    status: str = Field(default="success")
    dream_id: Optional[str] = None
    summary: Optional[str] = None


__all__ = [
    "DreamCategory",
    "DreamSymbol",
    "EmotionType",
    "ContentAnalysis",
    "LunarContext",
    "DreamAnalysisRequest",
    "DreamAnalysisResponse",
]
