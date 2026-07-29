"""`POST /api/v1/chart` — the thin core, for the web app and the PWA.

This is the one paid call in the product. Everything a client does with
a chart afterwards — angles anywhere on Earth, house cusps, aspects,
dignities, astrocartography lines, relocation — is computed from this
payload locally by `packages/chart-kit`, at no further cost and with no
network. That is why the gate belongs here rather than on features: one
ephemeris computation per chart buys unlimited exploration of it.

The MCP tool `calculate_natal_chart` returns the very same `chart_core`
object inside its richer response. `test_chart_core_contract.py` asserts
the two are byte-identical for identical input — a client must never
behave differently depending on which door it came through.
"""

from __future__ import annotations

import logging
from datetime import date as date_cls, time as time_cls
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from backend.services.astrology.chart_contract import ChartResponse
from backend.services.astrology.chart_core import (
    CHART_CORE_MAX_BYTES,
    CHART_KIT_HOUSE_SYSTEMS,
    DEFAULT_HOUSE_SYSTEM,
    build_chart_response,
    chart_core_bytes,
)
from backend.services.astrology.geocoder import Geocoder, GeocodingError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chart", tags=["Chart"])


class ChartRequest(BaseModel):
    """Birth data for the core payload.

    Coordinates are preferred over a place name: the caller usually knows
    exactly which Zaporizhzhia it means, and a name lookup can only guess.
    When only a name is given the server geocodes it and echoes the
    resolved coordinates back inside `chart_core.birth`.
    """

    birth_date: date_cls
    birth_time: Optional[time_cls] = Field(
        None,
        description="Local clock time. Omit if unknown — angles and houses "
                    "then have no meaning and the client must not draw them.",
    )
    birth_place: str = Field(
        "", max_length=255,
        description="Display label, and the geocoding query when no "
                    "coordinates are supplied.",
    )
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    timezone_name: Optional[str] = Field(
        None,
        description="IANA zone override. Omitted, the zone comes from the "
                    "coordinates via tzdata, historical rules included.",
    )
    house_system: str = Field(
        DEFAULT_HOUSE_SYSTEM,
        description="Requested house system, restricted to those chart-kit "
                    f"can re-derive client-side ({', '.join(sorted(CHART_KIT_HOUSE_SYSTEMS))}). "
                    "Beyond the polar circle Placidus is undefined; the "
                    "response then declares the system actually used and why.",
    )
    locale: str = Field("ru", pattern="^(en|ru)$")

    @model_validator(mode="after")
    def _coordinates_come_as_a_pair(self) -> "ChartRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "latitude and longitude must be provided together — one "
                "without the other cannot locate a birth place"
            )
        if self.latitude is None and not self.birth_place.strip():
            raise ValueError(
                "supply either coordinates or a birth_place to geocode"
            )
        return self


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    response_model=ChartResponse,
    # The two optional fields are ABSENT rather than null when they do not
    # apply, which is what the MCP surface emits — with them nulled the
    # HTTP body would stop being byte-identical, and clients would have to
    # learn a second shape of the same contract.
    response_model_exclude_none=True,
)
async def compute_chart(req: ChartRequest) -> dict[str, Any]:
    """Compute the self-contained chart core.

    Returns `chart_core` plus provenance and disclaimer. The payload is
    ~1.7 KB and is everything a client needs; it is safe to cache in
    localStorage/IndexedDB and to use with no network afterwards.
    """
    lat, lon = req.latitude, req.longitude
    if lat is None:
        try:
            location = await Geocoder().geocode(req.birth_place)
        except GeocodingError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not resolve birth place: {exc}",
            ) from exc
        lat, lon = location.latitude, location.longitude
        timezone_name = req.timezone_name or location.timezone
    else:
        timezone_name = req.timezone_name

    try:
        body = build_chart_response(
            birth_date=req.birth_date,
            birth_time=req.birth_time,
            lat=lat,
            lon=lon,
            place_label=req.birth_place,
            timezone_name=timezone_name,
            house_system=req.house_system,
            locale=req.locale,
        )
    except ValueError as exc:
        # Out of ephemeris coverage, or an unknown house system: a caller
        # error, answered as one rather than as a 500.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    size = chart_core_bytes(body["chart_core"])
    if size > CHART_CORE_MAX_BYTES:
        # The budget is a product promise (the payload must stay cheap to
        # ship and store), so breaching it is a bug worth a loud log even
        # though the answer itself is correct.
        logger.error(
            "chart_core exceeded its byte budget: %d > %d",
            size, CHART_CORE_MAX_BYTES,
        )
    return body
