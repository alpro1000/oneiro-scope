"""Attach a "what else can I compute" menu to tool responses.

The problem. The server registers 46 tools. A chat that lands on one of them
sees only that one — it has no way to discover that the same birth data also
buys a money contour, a decade map, astrocartography over a city pool or a
Solar Return. `analysis_plan` answered this from the start, but only if the
model thought to ask, and it usually did not. So the answer travels with the
data instead: every substantive response carries `can_also_compute`.

Offered, not run. Firing everything on each call would cost minutes and quota —
a decade map scans ten years at a 10-day step, a city scan runs a whole pool,
and a Solar Return suggestion computes one return per candidate city. The menu
lists only steps whose inputs are already satisfied, so the next call is one
step away, and separately lists what is blocked and on which question.

Domains follow the split the owner asked for: "astro" covers chart and face —
both read one standing person from static data — while "dreams" is per-episode
and shares no inputs with them.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from backend.services.strategic.analysis_plan import capability_menu

# Input keys, re-exported so call sites do not import from two modules.
from backend.services.strategic.analysis_plan import (  # noqa: F401
    BIRTH_DATE,
    BIRTH_PLACE,
    BIRTH_TIME,
    CITIES,
    DREAM_TEXT,
    FACE_PHOTOS,
    PARTNER_BIRTH,
    SCAN_YEARS,
    START_YEAR,
    TARGET_DATE,
    TRAITS,
)

MENU_KEY = "can_also_compute"


def with_menu(
    result: Any,
    domain: str = "astro",
    known_inputs: Optional[Iterable[str]] = None,
    completed: Optional[Iterable[str]] = None,
    locale: str = "ru",
) -> Any:
    """Return `result` with a capability menu attached, when that is possible.

    Non-dict results (a bare list from a lookup tool, for instance) are returned
    untouched rather than being wrapped: changing a tool's return *shape* to
    carry a hint would break callers for no gain. A dict that already carries a
    menu is left alone too, so nesting helpers cannot double-attach.
    """
    if not isinstance(result, dict) or MENU_KEY in result:
        return result
    result[MENU_KEY] = capability_menu(
        domain=domain,
        known_inputs=known_inputs,
        completed=completed,
        locale=locale,
    )
    return result


def birth_inputs(
    birth_date: Optional[str] = None,
    birth_time: Optional[str] = None,
    birth_place: Optional[str] = None,
    has_coordinates: bool = False,
) -> list[str]:
    """Translate a tool's own arguments into plan input keys.

    `has_coordinates` counts as knowing the birth place: the plan cares whether
    the location is pinned down, not how it was resolved, and a caller that
    passed latitude/longitude has pinned it more firmly than a name would.
    """
    known: list[str] = []
    if birth_date:
        known.append(BIRTH_DATE)
    if birth_time:
        known.append(BIRTH_TIME)
    if birth_place or has_coordinates:
        known.append(BIRTH_PLACE)
    return known
