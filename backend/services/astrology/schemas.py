"""Pydantic schemas for Astrology Service."""

from datetime import date, time, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ===== Provenance (v2.2 - Phase 2 Hardening) =====

class ProvenanceInfo(BaseModel):
    """Information about calculation sources and methodology."""
    ephemeris_engine: str = Field(
        description="Engine used: swieph (Swiss Ephemeris files) or moseph (Moshier algorithm)"
    )
    ephemeris_version: str = Field(
        description="Version of ephemeris data or algorithm"
    )
    calculation_timestamp: datetime = Field(
        description="UTC timestamp when calculation was performed"
    )
    methodology: str = Field(
        description="Astronomical calculation methodology (e.g., 'Placidus houses')"
    )
    accuracy_statement: str = Field(
        description="Expected accuracy of calculations"
    )


class ZodiacSign(str, Enum):
    """Zodiac signs."""
    ARIES = "aries"
    TAURUS = "taurus"
    GEMINI = "gemini"
    CANCER = "cancer"
    LEO = "leo"
    VIRGO = "virgo"
    LIBRA = "libra"
    SCORPIO = "scorpio"
    SAGITTARIUS = "sagittarius"
    CAPRICORN = "capricorn"
    AQUARIUS = "aquarius"
    PISCES = "pisces"


class Planet(str, Enum):
    """Celestial bodies used in astrology."""
    SUN = "sun"
    MOON = "moon"
    MERCURY = "mercury"
    VENUS = "venus"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptune"
    PLUTO = "pluto"
    NORTH_NODE = "north_node"
    SOUTH_NODE = "south_node"
    CHIRON = "chiron"


class AspectType(str, Enum):
    """Aspect types between planets."""
    CONJUNCTION = "conjunction"      # 0°
    SEXTILE = "sextile"              # 60°
    SQUARE = "square"                # 90°
    TRINE = "trine"                  # 120°
    OPPOSITION = "opposition"        # 180°
    QUINCUNX = "quincunx"           # 150°


class HoroscopePeriod(str, Enum):
    """Horoscope period types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class EventType(str, Enum):
    """Types of events for forecasting."""
    TRAVEL = "travel"
    WEDDING = "wedding"
    BUSINESS = "business"
    INTERVIEW = "interview"
    SURGERY = "surgery"
    MOVING = "moving"
    CONTRACT = "contract"
    EXAM = "exam"
    DATE = "date"
    OTHER = "other"


# ===== Planet Position =====

class PlanetPosition(BaseModel):
    """Position of a planet in the zodiac."""
    planet: Planet
    sign: ZodiacSign
    degree: float = Field(ge=0, lt=360, description="Absolute degree (0-359.99)")
    sign_degree: float = Field(ge=0, lt=30, description="Degree within sign (0-29.99)")
    retrograde: bool = False
    house: Optional[int] = Field(None, ge=1, le=12)


# ===== Aspect =====

class Aspect(BaseModel):
    """Aspect between two planets."""
    planet1: Planet
    planet2: Planet
    aspect_type: AspectType
    orb: float = Field(ge=0, le=10, description="Orb in degrees")
    applying: bool = Field(description="True if aspect is applying, False if separating")


# ===== House =====

class House(BaseModel):
    """Astrological house."""
    number: int = Field(ge=1, le=12)
    sign: ZodiacSign
    degree: float = Field(ge=0, lt=30)
    planets: list[Planet] = []


# ===== Natal Chart =====

class NatalChartRequest(BaseModel):
    """Request for natal chart calculation."""
    birth_date: date
    birth_time: Optional[time] = Field(
        None,
        description="Birth time. If unknown, 12:00 noon will be used"
    )
    birth_place: str = Field(
        min_length=2,
        max_length=255,
        description="Birth place (city, country)"
    )
    locale: str = Field(default="ru", pattern="^(en|ru)$")


class NatalChartResponse(BaseModel):
    """Response with natal chart data."""
    id: UUID
    user_id: Optional[UUID] = None
    birth_date: date
    birth_time: Optional[time]
    birth_place: str
    latitude: Decimal
    longitude: Decimal
    timezone: str

    # Calculated data
    sun_sign: ZodiacSign
    moon_sign: ZodiacSign
    ascendant: Optional[ZodiacSign] = Field(
        None,
        description="Ascendant sign (requires birth time)"
    )
    midheaven: Optional[ZodiacSign] = Field(
        None,
        description="Midheaven (MC) sign (requires birth time)"
    )

    planets: list[PlanetPosition]
    houses: Optional[list[House]] = Field(
        None,
        description="Houses (requires birth time)"
    )
    aspects: list[Aspect]

    # LLM interpretation
    interpretation: Optional[str] = None

    # Metadata
    created_at: datetime
    calculation_method: str = "swiss_ephemeris"
    provenance: Optional[ProvenanceInfo] = Field(
        None,
        description="Information about calculation sources and methodology"
    )


# ===== Horoscope =====

class HoroscopeRequest(BaseModel):
    """Request for horoscope generation."""
    natal_chart_id: Optional[UUID] = None
    period: HoroscopePeriod = HoroscopePeriod.DAILY
    target_date: Optional[date] = Field(
        None,
        description="Target date. Defaults to today"
    )
    locale: str = Field(default="ru", pattern="^(en|ru)$")


class TransitInfo(BaseModel):
    """Information about a transit."""
    transiting_planet: Planet
    natal_planet: Planet
    aspect: AspectType
    exact_date: date
    orb: float
    description: str


class HoroscopeResponse(BaseModel):
    """Response with horoscope data."""
    id: UUID
    user_id: Optional[UUID] = None
    natal_chart_id: Optional[UUID] = None
    period: HoroscopePeriod
    period_start: date
    period_end: date

    # Current transits
    transits: list[TransitInfo]
    retrograde_planets: list[Planet]
    lunar_phase: str
    lunar_day: int

    # LLM interpretation
    summary: str
    love_and_relationships: Optional[str] = None
    career_and_finance: Optional[str] = None
    health_and_wellness: Optional[str] = None
    recommendations: list[str]

    # Metadata
    created_at: datetime
    provenance: Optional[ProvenanceInfo] = Field(
        None,
        description="Information about calculation sources and methodology"
    )


# ===== Event Forecast =====

class EventForecastRequest(BaseModel):
    """Request for event favorability forecast."""
    natal_chart_id: Optional[UUID] = None
    event_date: date
    event_type: EventType
    event_location: Optional[str] = Field(
        None,
        max_length=255,
        description="Location of the event"
    )
    event_description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Additional details about the event"
    )
    locale: str = Field(default="ru", pattern="^(en|ru)$")


class EventForecastResponse(BaseModel):
    """Response with event forecast."""
    id: UUID
    user_id: Optional[UUID] = None
    natal_chart_id: Optional[UUID] = None
    event_date: date
    event_type: EventType
    event_location: Optional[str]

    # Forecast results
    favorability_score: int = Field(ge=0, le=100)
    favorability_level: str = Field(
        description="excellent/good/neutral/challenging/difficult"
    )

    # Transits on event date
    transits: list[TransitInfo]
    retrograde_planets: list[Planet]
    lunar_phase: str
    lunar_day: int

    # Analysis
    positive_factors: list[str]
    risk_factors: list[str]
    recommendations: list[str]

    # Alternative dates if unfavorable
    alternative_dates: Optional[list[date]] = Field(
        None,
        description="Better alternative dates within ±7 days"
    )

    # Metadata
    created_at: datetime
    provenance: Optional[ProvenanceInfo] = Field(
        None,
        description="Information about calculation sources and methodology"
    )


# ===== Voice Input =====

class VoiceInputRequest(BaseModel):
    """Request for voice input processing."""
    context: str = Field(
        default="general",
        pattern="^(dream|astrology|general)$",
        description="Context for better recognition"
    )
    language: str = Field(default="auto", pattern="^(ru|en|auto)$")


class VoiceInputResponse(BaseModel):
    """Response from voice input processing."""
    text: str
    language_detected: str
    confidence: float = Field(ge=0, le=1)
    duration_ms: int
    context: str
