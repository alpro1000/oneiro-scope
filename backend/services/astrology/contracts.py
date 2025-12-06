"""Strict input/output contracts for Astrology Service v2.0."""

from datetime import date, time, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============ ENUMS ============

class HoroscopePeriod(str, Enum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class ZodiacSign(str, Enum):
    ARIES = "Aries"
    TAURUS = "Taurus"
    GEMINI = "Gemini"
    CANCER = "Cancer"
    LEO = "Leo"
    VIRGO = "Virgo"
    LIBRA = "Libra"
    SCORPIO = "Scorpio"
    SAGITTARIUS = "Sagittarius"
    CAPRICORN = "Capricorn"
    AQUARIUS = "Aquarius"
    PISCES = "Pisces"


class AspectType(str, Enum):
    CONJUNCTION = "Conjunction"
    SEXTILE = "Sextile"
    SQUARE = "Square"
    TRINE = "Trine"
    OPPOSITION = "Opposition"
    QUINCUNX = "Quincunx"


class PlanetName(str, Enum):
    SUN = "Sun"
    MOON = "Moon"
    MERCURY = "Mercury"
    VENUS = "Venus"
    MARS = "Mars"
    JUPITER = "Jupiter"
    SATURN = "Saturn"
    URANUS = "Uranus"
    NEPTUNE = "Neptune"
    PLUTO = "Pluto"
    NORTH_NODE = "North Node"
    SOUTH_NODE = "South Node"
    CHIRON = "Chiron"


# ============ INPUT CONTRACTS ============

class Coordinates(BaseModel):
    """Geographic coordinates."""
    lat: float = Field(ge=-90, le=90, description="Latitude")
    lon: float = Field(ge=-180, le=180, description="Longitude")


class HoroscopeInput(BaseModel):
    """
    Input contract for horoscope generation.

    Example:
    {
        "birth_date": "1990-05-15",
        "birth_time": "14:30",
        "birth_place": "Moscow",
        "period": "today",
        "aspects_orb": 8
    }
    """
    birth_date: date = Field(description="Date of birth (YYYY-MM-DD)")
    birth_time: Optional[time] = Field(
        None,
        description="Time of birth (HH:MM). If null, houses are not calculated"
    )
    birth_place: Optional[str] = Field(
        None,
        max_length=255,
        description="City name for geocoding"
    )
    coords: Optional[Coordinates] = Field(
        None,
        description="Direct coordinates (alternative to birth_place)"
    )
    period: HoroscopePeriod = Field(
        default=HoroscopePeriod.TODAY,
        description="Horoscope period"
    )
    aspects_orb: int = Field(
        default=8,
        ge=1,
        le=15,
        description="Orb for aspect calculation in degrees"
    )
    locale: Literal["en", "ru"] = Field(default="ru")

    @field_validator("birth_place", "coords")
    @classmethod
    def validate_location(cls, v, info):
        """Ensure at least one location method is provided."""
        return v

    def model_post_init(self, __context):
        """Validate that either birth_place or coords is provided."""
        if not self.birth_place and not self.coords:
            raise ValueError("Either 'birth_place' or 'coords' must be provided")


# ============ OUTPUT CONTRACTS ============

class GeocodingResult(BaseModel):
    """Geocoding resolution result."""
    resolved_place: str
    coords: Coordinates
    timezone: str


class PlanetPosition(BaseModel):
    """Position of a planet in the zodiac."""
    name: PlanetName
    degree: float = Field(ge=0, lt=360, description="Absolute ecliptic longitude")
    sign: ZodiacSign
    sign_degree: float = Field(ge=0, lt=30, description="Degree within sign")
    house: Optional[int] = Field(None, ge=1, le=12, description="House (null if no birth_time)")
    retrograde: bool = False


class AspectData(BaseModel):
    """Aspect between two planets."""
    planet1: PlanetName
    planet2: PlanetName
    type: AspectType
    orb: float = Field(ge=0, le=15)
    applying: bool = Field(description="True if aspect is forming, False if separating")


class HouseData(BaseModel):
    """House cusp data."""
    number: int = Field(ge=1, le=12)
    sign: ZodiacSign
    degree: float = Field(ge=0, lt=30)


class NatalChartData(BaseModel):
    """Complete natal chart data."""
    planets: list[PlanetPosition]
    houses: Optional[list[HouseData]] = Field(
        None,
        description="Null if birth_time not provided"
    )
    aspects: list[AspectData]


class TransitData(BaseModel):
    """Transit aspect to natal planet."""
    date: date
    transit_planet: PlanetName
    natal_planet: PlanetName
    aspect: AspectType
    orb: float
    interpretation: str


class PredictionData(BaseModel):
    """Horoscope prediction sections."""
    general: str
    personal: str
    social: str
    warnings: Optional[str] = None


class ProvenanceRecord(BaseModel):
    """Data source provenance."""
    source: str
    timestamp: datetime
    data: str
    query: Optional[str] = None
    result: Optional[str] = None


class HoroscopeMetadata(BaseModel):
    """Horoscope generation metadata."""
    generated_at: datetime
    input: HoroscopeInput
    geocoding: GeocodingResult


class HoroscopeData(BaseModel):
    """Complete horoscope data."""
    meta: HoroscopeMetadata
    natal_chart: NatalChartData
    transits: list[TransitData]
    prediction: PredictionData
    provenance: list[ProvenanceRecord]


class HoroscopeOutput(BaseModel):
    """
    Output contract for horoscope response.

    Guaranteed structure for all responses.
    """
    status: Literal["success", "partial", "error"]
    horoscope: Optional[HoroscopeData] = None
    summary: Optional[str] = Field(
        None,
        max_length=2000,
        description="Human-readable summary (300-500 words)"
    )
    warnings: list[str] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: str
    message: str
    suggestions: list[str] = Field(default_factory=list)


class ErrorOutput(BaseModel):
    """Error response contract."""
    status: Literal["error"] = "error"
    error: ErrorDetail


# ============ ERROR CODES ============

class ErrorCode:
    """Standard error codes."""
    GEOCODING_FAILED = "GEOCODING_FAILED"
    EPHEMERIS_UNAVAILABLE = "EPHEMERIS_UNAVAILABLE"
    INVALID_DATE = "INVALID_DATE"
    INVALID_COORDINATES = "INVALID_COORDINATES"
    LLM_ERROR = "LLM_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    VALIDATION_ERROR = "VALIDATION_ERROR"


# ============ QUALITY GATES ============

class QualityGates:
    """Quality validation thresholds."""

    # Planetary positions must be within 0.1° of ephemeris
    POSITION_TOLERANCE_DEGREES = 0.1

    # Summary must be 300-500 words
    SUMMARY_MIN_WORDS = 300
    SUMMARY_MAX_WORDS = 500

    # Each interpretation must reference a rule
    REQUIRE_RULE_REFERENCE = True

    # JSON must be valid
    REQUIRE_VALID_JSON = True

    @classmethod
    def validate_summary_length(cls, summary: str) -> tuple[bool, str]:
        """Validate summary word count."""
        words = len(summary.split())
        if words < cls.SUMMARY_MIN_WORDS:
            return False, f"Summary too short: {words} words (min {cls.SUMMARY_MIN_WORDS})"
        if words > cls.SUMMARY_MAX_WORDS:
            return False, f"Summary too long: {words} words (max {cls.SUMMARY_MAX_WORDS})"
        return True, "OK"
