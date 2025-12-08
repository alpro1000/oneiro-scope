"""Astrology API endpoints."""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.services.astrology import (
    AstrologyService,
    NatalChartRequest,
    NatalChartResponse,
    HoroscopeRequest,
    HoroscopeResponse,
    EventForecastRequest,
    EventForecastResponse,
)
from backend.services.astrology.schemas import HoroscopePeriod, EventType

router = APIRouter(prefix="/astrology", tags=["astrology"])


def get_astrology_service() -> AstrologyService:
    """Dependency to get astrology service instance."""
    return AstrologyService()


@router.post(
    "/natal-chart",
    response_model=NatalChartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calculate natal chart",
    description="""
    Calculate a natal (birth) chart based on birth data.

    **Required inputs:**
    - `birth_date`: Date of birth (YYYY-MM-DD)
    - `birth_place`: Place of birth (city, country)

    **Optional inputs:**
    - `birth_time`: Time of birth (HH:MM). If unknown, 12:00 noon is used.
      Note: Ascendant and houses require birth time.
    - `locale`: Language for interpretation (en/ru)

    **Returns:**
    - Planet positions in zodiac signs
    - House cusps (if birth time provided)
    - Aspects between planets
    - LLM-generated interpretation

    **Scientific basis:**
    Uses Swiss Ephemeris for astronomical calculations
    with accuracy < 1 arc second.
    """,
)
async def calculate_natal_chart(
    request: NatalChartRequest,
    service: AstrologyService = Depends(get_astrology_service),
    # user_id: Optional[UUID] = Depends(get_current_user_id),  # TODO: Add auth
) -> NatalChartResponse:
    """Calculate natal chart from birth data."""
    try:
        return await service.calculate_natal_chart(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate natal chart: {str(e)}",
        )


@router.get(
    "/horoscope",
    response_model=HoroscopeResponse,
    summary="Get horoscope",
    description="""
    Generate a horoscope for a given period.

    **Parameters:**
    - `period`: daily, weekly, monthly, or yearly
    - `date`: Target date (defaults to today)
    - `natal_chart_id`: Optional ID of saved natal chart for personalization
    - `locale`: Language for interpretation (en/ru)

    **Returns:**
    - Current planetary transits
    - Retrograde planets
    - Lunar phase and day
    - Interpretation by life areas (love, career, health)
    - Practical recommendations

    **Personalization:**
    If `natal_chart_id` is provided, horoscope is personalized
    based on transits to natal positions.
    """,
)
async def get_horoscope(
    period: HoroscopePeriod = Query(
        HoroscopePeriod.DAILY,
        description="Horoscope period",
    ),
    target_date: Optional[date] = Query(
        None,
        alias="date",
        description="Target date (defaults to today)",
    ),
    natal_chart_id: Optional[UUID] = Query(
        None,
        description="Natal chart ID for personalization",
    ),
    locale: str = Query(
        "ru",
        pattern="^(en|ru)$",
        description="Language",
    ),
    service: AstrologyService = Depends(get_astrology_service),
) -> HoroscopeResponse:
    """Get horoscope for a period."""
    request = HoroscopeRequest(
        natal_chart_id=natal_chart_id,
        period=period,
        target_date=target_date,
        locale=locale,
    )

    # TODO: Load natal chart from DB if natal_chart_id provided
    natal_chart = None

    try:
        return await service.generate_horoscope(request, natal_chart)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate horoscope: {str(e)}",
        )


@router.post(
    "/event-forecast",
    response_model=EventForecastResponse,
    summary="Forecast event favorability",
    description="""
    Calculate the astrological favorability of a planned event.

    **Required inputs:**
    - `event_date`: Date of the planned event
    - `event_type`: Type of event (travel, wedding, business, etc.)

    **Optional inputs:**
    - `natal_chart_id`: For personalized forecast
    - `event_location`: Location of the event
    - `event_description`: Additional details
    - `locale`: Language (en/ru)

    **Returns:**
    - Favorability score (0-100%)
    - Positive astrological factors
    - Risk factors to consider
    - Recommendations
    - Alternative dates (if original date is unfavorable)

    **Methodology:**
    Analyzes transits to natal chart, Moon phase,
    and retrograde planets relevant to the event type.
    """,
)
async def forecast_event(
    request: EventForecastRequest,
    service: AstrologyService = Depends(get_astrology_service),
) -> EventForecastResponse:
    """Forecast favorability of an event."""
    # TODO: Load natal chart from DB if natal_chart_id provided
    natal_chart = None

    try:
        return await service.forecast_event(request, natal_chart)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to forecast event: {str(e)}",
        )


@router.get(
    "/event-types",
    summary="List supported event types",
    description="Get list of supported event types for forecasting.",
)
async def list_event_types() -> dict:
    """List available event types."""
    return {
        "event_types": [
            {
                "value": e.value,
                "label_en": e.value.replace("_", " ").title(),
                "label_ru": {
                    "travel": "Путешествие",
                    "wedding": "Свадьба",
                    "business": "Бизнес-сделка",
                    "interview": "Собеседование",
                    "surgery": "Операция",
                    "moving": "Переезд",
                    "contract": "Подписание контракта",
                    "exam": "Экзамен",
                    "date": "Свидание",
                    "other": "Другое",
                }.get(e.value, e.value),
            }
            for e in EventType
        ]
    }


@router.get(
    "/retrograde",
    summary="Get retrograde planets",
    description="Get list of retrograde planets on a specific date.",
)
async def get_retrograde_planets(
    target_date: Optional[date] = Query(
        None,
        alias="date",
        description="Date to check (defaults to today)",
    ),
    service: AstrologyService = Depends(get_astrology_service),
) -> dict:
    """Get retrograde planets on a date."""
    check_date = target_date or date.today()

    retrograde = service.transit_calculator.get_retrograde_planets(check_date)

    return {
        "date": check_date.isoformat(),
        "retrograde_planets": [
            {
                "planet": p.value,
                "description_ru": {
                    "mercury": "Избегайте подписания документов и важных переговоров",
                    "venus": "Будьте осторожны в романтических отношениях",
                    "mars": "Контролируйте импульсивность",
                    "jupiter": "Пересмотрите планы расширения",
                    "saturn": "Время для внутренней работы",
                    "uranus": "Внутренние перемены важнее внешних",
                    "neptune": "Усильте практику осознанности",
                    "pluto": "Глубокая трансформация",
                }.get(p.value, ""),
                "description_en": {
                    "mercury": "Avoid signing documents and important negotiations",
                    "venus": "Be cautious in romantic relationships",
                    "mars": "Control impulsiveness",
                    "jupiter": "Review expansion plans",
                    "saturn": "Time for inner work",
                    "uranus": "Inner changes matter more than external",
                    "neptune": "Strengthen mindfulness practice",
                    "pluto": "Deep transformation",
                }.get(p.value, ""),
            }
            for p in retrograde
        ],
    }
