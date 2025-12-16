"""Main Astrology Service orchestrator."""

import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from .schemas import (
    AspectType,
    EventForecastRequest,
    EventForecastResponse,
    EventType,
    HoroscopePeriod,
    HoroscopeRequest,
    HoroscopeResponse,
    NatalChartRequest,
    NatalChartResponse,
    Planet,
    TransitInfo,
    ZodiacSign,
)
from .ephemeris import SwissEphemeris
from .natal_chart import NatalChartCalculator
from .transits import TransitCalculator
from .geocoder import Geocoder, GeocodingError
from .interpreter import AstrologyInterpreter

logger = logging.getLogger(__name__)


class AstrologyService:
    """
    Main service for astrological calculations and interpretations.

    Provides:
    - Natal chart calculation
    - Horoscope generation
    - Event favorability forecasting

    Uses Swiss Ephemeris for astronomical accuracy.
    """

    def __init__(
        self,
        ephemeris: Optional[SwissEphemeris] = None,
        geocoder: Optional[Geocoder] = None,
        interpreter: Optional[AstrologyInterpreter] = None,
    ):
        self.ephemeris = ephemeris or SwissEphemeris()
        self.geocoder = geocoder or Geocoder()
        self.interpreter = interpreter or AstrologyInterpreter()
        self.natal_calculator = NatalChartCalculator(self.ephemeris)
        self.transit_calculator = TransitCalculator(self.ephemeris)

    async def calculate_natal_chart(
        self,
        request: NatalChartRequest,
        user_id: Optional[UUID] = None,
    ) -> NatalChartResponse:
        """
        Calculate natal chart based on birth data.

        Args:
            request: Birth data (date, time, place)
            user_id: Optional user ID to associate chart with

        Returns:
            Complete natal chart with planets, houses, aspects, and interpretation
        """
        logger.info(f"Calculating natal chart for {request.birth_place}")

        # Geocode birth place
        try:
            location = self.geocoder.geocode(request.birth_place)
        except GeocodingError as exc:
            raise ValueError(f"Geocoding failed: {exc}") from exc
        if not location:
            raise ValueError(f"Could not geocode location: {request.birth_place}")

        # Use noon if time not provided
        birth_time = request.birth_time or time(12, 0)
        birth_datetime = datetime.combine(request.birth_date, birth_time)

        # Calculate planet positions
        planets = self.natal_calculator.calculate_planets(
            birth_datetime,
            location.latitude,
            location.longitude,
            location.timezone,
        )

        # Calculate houses (only if birth time is known)
        houses = None
        ascendant = None
        midheaven = None
        if request.birth_time:
            houses = self.natal_calculator.calculate_houses(
                birth_datetime,
                location.latitude,
                location.longitude,
                location.timezone,
            )
            if houses:
                ascendant = houses[0].sign  # 1st house cusp
                midheaven = houses[9].sign  # 10th house cusp (MC)

        # Calculate aspects
        aspects = self.natal_calculator.calculate_aspects(planets)

        # Get Sun and Moon signs
        sun_position = next(p for p in planets if p.planet == Planet.SUN)
        moon_position = next(p for p in planets if p.planet == Planet.MOON)

        # Generate interpretation via LLM
        interpretation = await self.interpreter.interpret_natal_chart(
            planets=planets,
            houses=houses,
            aspects=aspects,
            locale=request.locale,
        )

        return NatalChartResponse(
            id=uuid4(),
            user_id=user_id,
            birth_date=request.birth_date,
            birth_time=request.birth_time,
            birth_place=request.birth_place,
            latitude=Decimal(str(location.latitude)),
            longitude=Decimal(str(location.longitude)),
            timezone=location.timezone,
            sun_sign=sun_position.sign,
            moon_sign=moon_position.sign,
            ascendant=ascendant,
            midheaven=midheaven,
            planets=planets,
            houses=houses,
            aspects=aspects,
            interpretation=interpretation,
            created_at=datetime.utcnow(),
        )

    async def generate_horoscope(
        self,
        request: HoroscopeRequest,
        natal_chart: Optional[NatalChartResponse] = None,
        user_id: Optional[UUID] = None,
    ) -> HoroscopeResponse:
        """
        Generate horoscope for a given period.

        Args:
            request: Horoscope parameters (period, date)
            natal_chart: Optional natal chart for personalized horoscope
            user_id: Optional user ID

        Returns:
            Horoscope with transits and interpretation
        """
        target_date = request.target_date or date.today()
        logger.info(f"Generating {request.period} horoscope for {target_date}")

        # Determine period boundaries
        period_start, period_end = self._get_period_boundaries(
            target_date, request.period
        )

        # Calculate transits
        transits = []
        retrograde_planets = []

        if natal_chart:
            transits = self.transit_calculator.calculate_transits(
                natal_chart.planets,
                period_start,
                period_end,
            )
            retrograde_planets = self.transit_calculator.get_retrograde_planets(
                target_date
            )

        # Get lunar info
        lunar_phase, lunar_day = self.ephemeris.get_lunar_info(target_date)

        # Generate interpretation
        summary, sections, recommendations = await self.interpreter.interpret_horoscope(
            transits=transits,
            retrograde_planets=retrograde_planets,
            lunar_phase=lunar_phase,
            lunar_day=lunar_day,
            period=request.period,
            locale=request.locale,
        )

        return HoroscopeResponse(
            id=uuid4(),
            user_id=user_id,
            natal_chart_id=request.natal_chart_id,
            period=request.period,
            period_start=period_start,
            period_end=period_end,
            transits=transits,
            retrograde_planets=retrograde_planets,
            lunar_phase=lunar_phase,
            lunar_day=lunar_day,
            summary=summary,
            love_and_relationships=sections.get("love"),
            career_and_finance=sections.get("career"),
            health_and_wellness=sections.get("health"),
            recommendations=recommendations,
            created_at=datetime.utcnow(),
        )

    async def forecast_event(
        self,
        request: EventForecastRequest,
        natal_chart: Optional[NatalChartResponse] = None,
        user_id: Optional[UUID] = None,
    ) -> EventForecastResponse:
        """
        Forecast favorability of an event on a specific date.

        Args:
            request: Event details (date, type, location)
            natal_chart: Optional natal chart for personalized forecast
            user_id: Optional user ID

        Returns:
            Forecast with favorability score and recommendations
        """
        logger.info(f"Forecasting {request.event_type} event on {request.event_date}")

        # Calculate transits for event date
        transits = []
        if natal_chart:
            transits = self.transit_calculator.calculate_transits(
                natal_chart.planets,
                request.event_date,
                request.event_date,
            )

        retrograde_planets = self.transit_calculator.get_retrograde_planets(
            request.event_date
        )

        # Get lunar info
        lunar_phase, lunar_day = self.ephemeris.get_lunar_info(request.event_date)

        # Calculate favorability score
        favorability_score, positive_factors, risk_factors = (
            self._calculate_favorability(
                transits=transits,
                retrograde_planets=retrograde_planets,
                lunar_phase=lunar_phase,
                lunar_day=lunar_day,
                event_type=request.event_type,
            )
        )

        # Get favorability level
        favorability_level = self._score_to_level(favorability_score)

        # Find alternative dates if score is low
        alternative_dates = None
        if favorability_score < 50:
            alternative_dates = await self._find_better_dates(
                request.event_date,
                request.event_type,
                natal_chart,
            )

        # Generate recommendations
        recommendations = await self.interpreter.generate_event_recommendations(
            event_type=request.event_type,
            transits=transits,
            positive_factors=positive_factors,
            risk_factors=risk_factors,
            locale=request.locale,
        )

        return EventForecastResponse(
            id=uuid4(),
            user_id=user_id,
            natal_chart_id=request.natal_chart_id,
            event_date=request.event_date,
            event_type=request.event_type,
            event_location=request.event_location,
            favorability_score=favorability_score,
            favorability_level=favorability_level,
            transits=transits,
            retrograde_planets=retrograde_planets,
            lunar_phase=lunar_phase,
            lunar_day=lunar_day,
            positive_factors=positive_factors,
            risk_factors=risk_factors,
            recommendations=recommendations,
            alternative_dates=alternative_dates,
            created_at=datetime.utcnow(),
        )

    def _get_period_boundaries(
        self, target_date: date, period: HoroscopePeriod
    ) -> tuple[date, date]:
        """Calculate period start and end dates."""
        if period == HoroscopePeriod.DAILY:
            return target_date, target_date
        elif period == HoroscopePeriod.WEEKLY:
            # Week starts on Monday
            start = target_date - timedelta(days=target_date.weekday())
            end = start + timedelta(days=6)
            return start, end
        elif period == HoroscopePeriod.MONTHLY:
            start = target_date.replace(day=1)
            # Next month first day - 1 day
            if target_date.month == 12:
                end = date(target_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)
            return start, end
        else:  # YEARLY
            start = date(target_date.year, 1, 1)
            end = date(target_date.year, 12, 31)
            return start, end

    def _calculate_favorability(
        self,
        transits: list[TransitInfo],
        retrograde_planets: list[Planet],
        lunar_phase: str,
        lunar_day: int,
        event_type: EventType,
    ) -> tuple[int, list[str], list[str]]:
        """
        Calculate event favorability score.

        Returns:
            Tuple of (score 0-100, positive_factors, risk_factors)
        """
        score = 50  # Base score
        positive_factors = []
        risk_factors = []

        # Analyze transits
        for transit in transits:
            if transit.aspect in [AspectType.TRINE, AspectType.SEXTILE]:
                score += 5
                positive_factors.append(
                    f"{transit.transiting_planet.value} {transit.aspect.value} "
                    f"{transit.natal_planet.value}"
                )
            elif transit.aspect in [AspectType.SQUARE, AspectType.OPPOSITION]:
                score -= 5
                risk_factors.append(
                    f"{transit.transiting_planet.value} {transit.aspect.value} "
                    f"{transit.natal_planet.value}"
                )

        # Retrograde penalties (context-dependent)
        retrograde_penalties = {
            Planet.MERCURY: ["contract", "interview", "exam"],
            Planet.VENUS: ["wedding", "date"],
            Planet.MARS: ["surgery", "business"],
        }

        for planet in retrograde_planets:
            if planet in retrograde_penalties:
                affected_events = retrograde_penalties[planet]
                if event_type.value in affected_events:
                    score -= 15
                    risk_factors.append(f"{planet.value} ретроградный")
                else:
                    score -= 5

        # Lunar phase influence
        favorable_phases = {
            "new_moon": ["business", "contract"],
            "waxing_crescent": ["interview", "exam"],
            "first_quarter": ["business", "moving"],
            "waxing_gibbous": ["wedding", "date"],
            "full_moon": ["travel"],
            "waning_gibbous": ["surgery"],
            "last_quarter": ["moving"],
            "waning_crescent": ["surgery"],
        }

        if event_type.value in favorable_phases.get(lunar_phase, []):
            score += 10
            positive_factors.append(f"Благоприятная лунная фаза: {lunar_phase}")

        # Clamp score
        score = max(0, min(100, score))

        return score, positive_factors, risk_factors

    def _score_to_level(self, score: int) -> str:
        """Convert numerical score to level."""
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "neutral"
        elif score >= 20:
            return "challenging"
        else:
            return "difficult"

    async def _find_better_dates(
        self,
        original_date: date,
        event_type: EventType,
        natal_chart: Optional[NatalChartResponse],
    ) -> list[date]:
        """Find better alternative dates within ±7 days."""
        alternatives = []

        for delta in range(-7, 8):
            if delta == 0:
                continue

            check_date = original_date + timedelta(days=delta)
            transits = []
            if natal_chart:
                transits = self.transit_calculator.calculate_transits(
                    natal_chart.planets,
                    check_date,
                    check_date,
                )

            retrograde_planets = self.transit_calculator.get_retrograde_planets(
                check_date
            )
            lunar_phase, lunar_day = self.ephemeris.get_lunar_info(check_date)

            score, _, _ = self._calculate_favorability(
                transits=transits,
                retrograde_planets=retrograde_planets,
                lunar_phase=lunar_phase,
                lunar_day=lunar_day,
                event_type=event_type,
            )

            if score >= 60:
                alternatives.append((check_date, score))

        # Sort by score descending, return top 3 dates
        alternatives.sort(key=lambda x: x[1], reverse=True)
        return [d[0] for d in alternatives[:3]]
