"""Astrology API endpoints."""

from datetime import date, datetime, time as time_cls, timezone
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

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


# --- Astrocartography (interactive relocation map) ---------------------------

_ACG_DISCLAIMER = (
    "Reflective / entertainment content. Angle geometry is astronomy "
    "(Swiss Ephemeris); the work/life summary is a rule-based reflection, "
    "not a prediction, and not medical, psychological, legal or financial "
    "advice. Results depend on an accurate birth time."
)


class AstrocartographyBirth(BaseModel):
    """Birth data needed to anchor the relocation chart."""

    birth_date: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    birth_time: Optional[time_cls] = Field(
        None, description="Time of birth (HH:MM). Noon is used if omitted."
    )
    birth_timezone: str = Field(
        "UTC", description="IANA timezone of birth, e.g. 'Europe/Kyiv'."
    )
    birth_lat: float = Field(0.0, ge=-90, le=90, description="Birth latitude.")
    birth_lon: float = Field(0.0, ge=-180, le=180, description="Birth longitude.")
    birth_place: Optional[str] = Field(None, description="Birth place label.")


class AstrocartographyPointRequest(AstrocartographyBirth):
    """Birth data + a clicked location to inspect."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude to inspect.")
    lon: float = Field(..., ge=-180, le=180, description="Longitude to inspect.")
    locale: str = Field("ru", pattern="^(en|ru)$", description="Summary language.")


def _natal_jd(b: AstrocartographyBirth) -> float:
    """Convert birth data → Julian Day (UT). Noon local if time unknown."""
    import swisseph as swe

    t = b.birth_time or time_cls(12, 0)
    try:
        tz = ZoneInfo(b.birth_timezone)
    except Exception:
        tz = timezone.utc
    local = datetime(
        b.birth_date.year, b.birth_date.month, b.birth_date.day,
        t.hour, t.minute, getattr(t, "second", 0), tzinfo=tz,
    )
    utc = local.astimezone(timezone.utc)
    return swe.julday(
        utc.year, utc.month, utc.day,
        utc.hour + utc.minute / 60.0 + utc.second / 3600.0,
    )


@router.post(
    "/astrocartography/chart",
    summary="Astrocartography lines for the interactive map",
    description=(
        "Return the full astrocartography line set (GeoJSON) plus a compact "
        "chart payload (sidereal time, obliquity, planet ecliptic + equatorial "
        "coordinates, birth point). A thin client can compute the four angles "
        "for any clicked location from this payload without an ephemeris. "
        "Pure geometry — no interpretation."
    ),
)
async def astrocartography_chart(req: AstrocartographyBirth) -> dict:
    """Compute astrocartography lines + chart geometry for a birth moment."""
    from backend.services.astrology.astrocartography import (
        acg_lines,
        chart_geometry,
    )

    try:
        jd = _natal_jd(req)
        return {
            "layer": "astronomy",
            "methodology": (
                "Astro*Carto*Graphy (Lewis 1976); Swiss Ephemeris MOSEPH"
            ),
            "chart": chart_geometry(
                jd, req.birth_lat, req.birth_lon, req.birth_place or "birth"
            ),
            "lines": acg_lines(jd),
            "disclaimer": _ACG_DISCLAIMER,
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute astrocartography: {str(e)}",
        )


@router.post(
    "/astrocartography/point",
    summary="Inspect one location: four angles + plain-language summary",
    description=(
        "Relocate the chart to a clicked point and return the four angles "
        "(Asc/MC/IC/Desc), the natal planets on those angles within orb, and "
        "a rule-based work/life summary in plain language (ru/en)."
    ),
)
async def astrocartography_point(req: AstrocartographyPointRequest) -> dict:
    """Relocate to a point and summarise it."""
    from backend.services.astrology.astrocartography import (
        relocate,
        relocation_summary,
    )

    try:
        jd = _natal_jd(req)
        result = relocate(jd, req.lat, req.lon, orb_deg=8.0)
        return {
            "location": {"lat": req.lat, "lon": req.lon},
            "angles": {
                "asc": result.asc,
                "mc": result.mc,
                "ic": result.ic,
                "desc": result.desc,
            },
            "contacts": [
                {
                    "planet": h.planet,
                    "angle": h.angle,
                    "orb_deg": h.orb_deg,
                    "planet_longitude": h.planet_longitude,
                    "angle_longitude": h.angle_longitude,
                }
                for h in result.angle_hits
            ],
            "score": result.score,
            "summary": relocation_summary(result, locale=req.locale),
            "disclaimer": _ACG_DISCLAIMER,
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to inspect location: {str(e)}",
        )


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


@router.get(
    "/cities/search",
    summary="Search cities for autocomplete",
    description="""
    Search for cities by name with autocomplete support.

    **Parameters:**
    - `query`: City name to search (minimum 2 characters)
    - `locale`: Language for results (en/ru)
    - `max_results`: Maximum number of results (default: 10)

    **Returns:**
    - List of cities with name, country, coordinates, and display format

    **Example:**
    - Query: "Моск" → Returns: Moscow, Russia (55.75, 37.62)
    - Query: "Par" → Returns: Paris, France (48.86, 2.35)
    """,
)
async def search_cities(
    query: str = Query(
        ...,
        min_length=2,
        description="City name to search",
    ),
    locale: str = Query(
        "ru",
        pattern="^(en|ru)$",
        description="Language for results",
    ),
    max_results: int = Query(
        10,
        ge=1,
        le=50,
        description="Maximum number of results",
    ),
) -> dict:
    """Search cities for autocomplete."""
    from backend.utils.geonames_resolver import geonames_search_cities

    try:
        cities = await geonames_search_cities(query, max_results=max_results)

        return {
            "query": query,
            "cities": [
                {
                    "name": city["name"],
                    "country": city["country"],
                    "admin_name": city.get("admin_name", ""),
                    "lat": city["lat"],
                    "lon": city["lon"],
                    "display": city["display"],
                    "geoname_id": city.get("geoname_id"),
                }
                for city in cities
            ],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search cities: {str(e)}",
        )
