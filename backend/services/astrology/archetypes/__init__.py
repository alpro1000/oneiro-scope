"""Hard archetype tables — classical astrology interpretation as data.

Each module here is a deterministic lookup table built from cited
classical / modern sources (Liz Greene, Sue Tompkins, Robert Hand,
Stephen Arroyo). These tables let the system surface archetype claims
**without invoking an LLM** — they sit at confidence 0.9 in the
ladder ("cited classical rule"), one tier below pure ephemeris
calculation (1.0) and above LLM synthesis (0.7).

Each lookup returns a dict with:
  - `archetype` — short label
  - `themes` — list of keywords
  - `description` — 1-2 paragraph text
  - `source` — citation (author, work, year, page)

The data is intentionally **traditional / generic** — personalisation
happens at the LLM synthesis layer using these as input.
"""

from backend.services.astrology.archetypes.aspects import ASPECTS
from backend.services.astrology.archetypes.dignities import (
    DIGNITIES,
    essential_dignity,
)
from backend.services.astrology.archetypes.houses import HOUSES
from backend.services.astrology.archetypes.mc_in_sign import MC_IN_SIGN
from backend.services.astrology.archetypes.planet_in_house import (
    PLANET_DRIVES,
    planet_in_house_archetype,
)
from backend.services.astrology.archetypes.sun_in_sign import SUN_IN_SIGN
from backend.services.astrology.archetypes.transit_meanings import (
    TRANSIT_AGENDA,
    transit_archetype,
)
from backend.services.astrology.archetypes.zodiac_signs import ZODIAC_SIGNS

__all__ = [
    "ASPECTS",
    "DIGNITIES",
    "essential_dignity",
    "HOUSES",
    "MC_IN_SIGN",
    "PLANET_DRIVES",
    "planet_in_house_archetype",
    "SUN_IN_SIGN",
    "TRANSIT_AGENDA",
    "transit_archetype",
    "ZODIAC_SIGNS",
]
