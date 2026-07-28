"""Attach a compact "what else can I compute" menu to tool responses.

The problem. A chat that lands on one tool sees only that one — it cannot
discover that the same birth data also buys a money contour or a Solar
Return. `analysis_plan` answered this from the start, but only if the
model thought to ask, and it usually did not. So the answer travels with
the data: every substantive response carries `can_also_compute`.

Compact since WP-11. The first version attached the full ready/blocked/
questions structure; a live audit measured ~90k chars of menu across one
conversation — the menu had become the payload. The block is now
`{"next": [≤3 ready tools], "full_plan_tool": "analysis_plan"}`, ≤200
chars by test, and everything else lives one call away in analysis_plan.

Domains follow the owner's split: "astro" reads one standing person from
static data; "dreams" is per-episode and shares no inputs with it.
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
    POINT,
    SCAN_YEARS,
    START_YEAR,
    TARGET_DATE,
    TRAITS,
    USER_ID,
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
