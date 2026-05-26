"""Dream analysis MCP tools.

Wraps `backend.services.dreams.DreamService` for analysis, plus pure-data
lookups for symbols, archetypes, and Hall/Van de Castle categories.
"""

from __future__ import annotations

import json
from datetime import date as date_cls
from pathlib import Path
from typing import Any, Optional

from backend.services.dreams.schemas import (
    DreamAnalysisRequest,
    DreamCategory,
)
from backend.services.dreams.service import DreamService


_service: Optional[DreamService] = None
_KB_DIR = Path(__file__).resolve().parents[3] / "backend" / "services" / "dreams" / "knowledge_base"


def _svc() -> DreamService:
    global _service
    if _service is None:
        _service = DreamService()
    return _service


async def analyze_dream(
    dream_text: str,
    dream_date: Optional[str] = None,
    dreamer_gender: Optional[str] = None,
    dreamer_age_group: Optional[str] = None,
    locale: str = "ru",
) -> dict[str, Any]:
    """Analyze a dream using Hall/Van de Castle content analysis + Jungian
    archetypes + DreamBank norms + lunar context.

    Returns symbols, content analysis, primary emotion, themes, archetypes,
    norm comparison (typicality 0–100% if dreamer_gender is given), lunar
    context (if dream_date is given), narrative interpretation, and
    recommendations. Language is auto-detected from dream_text but locale
    controls the response language.

    Args:
        dream_text: Dream narrative (10–10000 characters).
        dream_date: YYYY-MM-DD of the dream. Enables lunar context.
        dreamer_gender: "male" or "female". Enables Hall/Van de Castle norm
            comparison.
        dreamer_age_group: Free-text age group (e.g., "20-30").
        locale: "ru" or "en". Response language.
    """
    req = DreamAnalysisRequest(
        dream_text=dream_text,
        dream_date=date_cls.fromisoformat(dream_date) if dream_date else None,
        dreamer_gender=dreamer_gender,
        dreamer_age_group=dreamer_age_group,
        locale=locale,
    )
    resp = await _svc().analyze_dream(req)
    return resp.model_dump(mode="json")


def list_dream_symbols(locale: str = "ru") -> list[dict[str, Any]]:
    """Return all known dream symbols with interpretations.

    The knowledge base currently holds 56 symbols (49 classical + 7 modern:
    surveillance, boundaries, control, escape_liberation, privacy, autonomy,
    technology). Each entry includes symbol name, category, Jungian archetype
    link, and bilingual interpretation.

    Args:
        locale: "ru" or "en". Filters which interpretation field is surfaced.
    """
    path = _KB_DIR / "symbols.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("symbols", [])
    out = []
    for item in items:
        out.append(
            {
                "symbol": item.get("symbol") or item.get("name"),
                "category": item.get("category"),
                "archetype": item.get("archetype"),
                "interpretation": item.get(f"interpretation_{locale}")
                or item.get("interpretation")
                or item.get("interpretation_en"),
            }
        )
    return out


def list_archetypes() -> list[str]:
    """List Jungian archetypes used by the dream interpreter.

    Returns: shadow, anima, animus, self, hero, transformation, persona,
    trickster, mother, father, child, wise_old_man. Used as a vocabulary
    when reading `analyze_dream` results.
    """
    return [
        "shadow",
        "anima",
        "animus",
        "self",
        "hero",
        "transformation",
        "persona",
        "trickster",
        "mother",
        "father",
        "child",
        "wise_old_man",
    ]


def list_hvdc_categories() -> list[str]:
    """List Hall/Van de Castle content analysis categories.

    Reference: Hall & Van de Castle, *The Content Analysis of Dreams* (1966).
    """
    return [c.value for c in DreamCategory]
