"""The response contract for `chart_core`, as Pydantic models.

Deliberately router-free. `build_chart_response` is the single producer
for both transports, so the schema that describes it belongs beside the
builder rather than inside the HTTP module: importing the contract must
not require importing FastAPI, and `test_chart_core_contract.py` proves
identity by reading these definitions without standing a server up.

Field order matters here and is not incidental. The acceptance criterion
is that the MCP body and the HTTP body are byte-identical; FastAPI
serialises through this model, so a reordered field would break that
while every value stayed correct. The order below mirrors
`chart_core.build_chart_core` line for line.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BodyState(BaseModel):
    """One body's state at the natal moment."""

    ecl_lon: float = Field(description="Ecliptic longitude, degrees 0–360.")
    ecl_lat: float = Field(description="Ecliptic latitude, degrees.")
    ra: float = Field(description="Right ascension — astrocartography loci.")
    dec: float = Field(description="Declination, degrees.")
    speed_lon: float = Field(description="Degrees/day; negative is retrograde.")
    retrograde: bool


class BirthInfo(BaseModel):
    lat: float
    lon: float
    tz_used: str = Field(description="IANA zone actually applied.")
    utc_offset_used: str = Field(description="±HH:MM, pre-formatted.")
    tz_source: str
    local_clock: str
    utc: str
    place_label: str = Field(
        description="Display echo of the requested place, bounded so a long "
                    "name cannot push the core past its byte budget."
    )
    time_known: bool = Field(
        description="False when no birth time was given: noon was assumed so "
                    "the slow bodies have a position, and the client MUST NOT "
                    "draw angles or houses."
    )


class ChartCoreModel(BaseModel):
    """The budgeted payload. Field order mirrors the builder exactly.

    Deliberately, not incidentally: `test_chart_core_contract.py` asserts
    the HTTP body and the MCP body serialise to identical bytes, and a
    reordered model would break that while every value stayed correct.
    """

    version: str
    jd_ut: float
    gmst: float = Field(description="Apparent sidereal time at Greenwich, degrees.")
    obliquity: float = Field(description="True obliquity — paired with gmst.")
    birth: BirthInfo
    bodies: dict[str, BodyState]
    node_type: str = Field(description="'true' | 'mean' lunar node.")
    house_system: str = Field(description="The system defined at the BIRTH latitude.")
    requested_house_system: Optional[str] = Field(
        None,
        description="Present only when the birth latitude forced a "
                    "substitution; relocation needs the original request.",
    )


class Provenance(BaseModel):
    ephemeris_engine: str
    ephemeris_version: str
    accuracy: str
    sidereal_time: str


class ChartResponse(BaseModel):
    """What both transports return. See `chart_core.build_chart_response`."""

    chart_core: ChartCoreModel
    provenance: Provenance
    how_to_read: str
    disclaimer: str
    house_system_note: Optional[str] = Field(
        None,
        description="Why the house system differs from the one requested. "
                    "Prose, kept out of the budgeted core.",
    )
