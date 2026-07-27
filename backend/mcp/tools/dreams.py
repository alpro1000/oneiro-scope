"""Dream analysis MCP tools.

Wraps `backend.services.dreams.DreamService` for analysis, plus pure-data
lookups for symbols, archetypes, and Hall/Van de Castle categories.

Data-first policy (same as `calculate_natal_chart`, PR #161): the MCP
client is a strong model — it reads the deterministic coding itself, so
the server-side prose interpretation is OFF by default and exists only
for clients without a model of their own. Every dreams response carries
the disclaimer.
"""

from __future__ import annotations

import json
from datetime import date as date_cls
from pathlib import Path
from typing import Any, Optional

from backend.mcp.tools._menu import DREAM_TEXT, with_menu
from backend.services.dreams.schemas import (
    DreamAnalysisRequest,
    DreamCategory,
)
from backend.services.dreams.service import DreamService
from backend.services.strategic.disclaimer import DISCLAIMERS, DISCLAIMER_RU


_service: Optional[DreamService] = None
_KB_DIR = Path(__file__).resolve().parents[3] / "backend" / "services" / "dreams" / "knowledge_base"


def _svc() -> DreamService:
    global _service
    if _service is None:
        _service = DreamService()
    return _service


def _disclaimer(locale: str) -> str:
    return DISCLAIMERS.get(locale, DISCLAIMER_RU)


async def analyze_dream(
    dream_text: str,
    dream_date: Optional[str] = None,
    dreamer_gender: Optional[str] = None,
    dreamer_age_group: Optional[str] = None,
    locale: str = "ru",  # ru | en | de | es | fr
    include_interpretation: bool = False,
) -> dict[str, Any]:
    """Analyze a dream: structural Hall/Van de Castle coding + symbols +
    Jungian archetypes + DreamBank norms + lunar context.

    Returns DETERMINISTIC data: characters (male/female/animal, distinct
    nouns), social interactions (aggression/friendliness/sexuality — each
    backed by an `hvdc_evidence` item citing the exact clause and coding
    rule), success/failure, misfortune/good fortune, emotions, symbols
    (negation-aware: «во сне не было воды» does not yield water), norm
    comparison vs Hall & Van de Castle (1966) college norms, and lunar
    context when dream_date is given. Indicators that cannot be computed
    (e.g. A/F index with zero interactions) arrive in
    `norm_comparison.insufficient_data` — never as fake zeros.

    You (the calling model) are expected to READ this coding yourself and
    interpret it, labelled: counts and evidence are deterministic (1.0),
    the symbol dictionary is 0.8, your synthesis is 0.7, and the response's
    disclaimer travels with any reading. That is why server-side prose is
    OFF by default — a second, weaker LLM hop would argue with its own
    extractor.

    Args:
        dream_text: Dream narrative (10–10000 characters).
        dream_date: YYYY-MM-DD of the dream. Enables lunar context.
        dreamer_gender: "male" or "female". Enables Hall/Van de Castle norm
            comparison.
        dreamer_age_group: Free-text age group (e.g., "20-30").
        locale: "ru" or "en". Response language.
        include_interpretation: Add server-generated prose (summary,
            interpretation, recommendations). Default False — only for a
            client with no model of its own; requires a server LLM key and
            degrades to a template without one.
    """
    req = DreamAnalysisRequest(
        dream_text=dream_text,
        dream_date=date_cls.fromisoformat(dream_date) if dream_date else None,
        dreamer_gender=dreamer_gender,
        dreamer_age_group=dreamer_age_group,
        locale=locale,
    )
    resp = await _svc().analyze_dream(req, interpret=include_interpretation)
    out = resp.model_dump(mode="json")

    # The MCP tool takes no physiological events, so the field can never be
    # non-empty on this path — drop it instead of shipping a dead [].
    out.pop("physiological_correlations", None)

    if not include_interpretation:
        out.pop("summary", None)
        out.pop("interpretation", None)
        out.pop("recommendations", None)
        out["how_to_read"] = (
            "Deterministic HVdC coding (1.0): content_analysis counts are "
            "backed clause-by-clause by hvdc_evidence. Interpret it yourself "
            "and label: counts 1.0, symbol dictionary 0.8, your synthesis "
            "0.7. Norm indicators listed in insufficient_data are undefined "
            "for this dream — do not read them as zeros."
        )
    return with_menu(
        out, domain="dreams",
        known_inputs=[DREAM_TEXT], completed=["dream"], locale=locale,
    )


def list_dream_symbols(locale: str = "ru") -> dict[str, Any]:
    """Return all known dream symbols with interpretations.

    The knowledge base currently holds 56 symbols (49 classical + 7 modern:
    surveillance, boundaries, control, escape_liberation, privacy, autonomy,
    technology). Each entry includes symbol name, category, Jungian archetype
    link, and bilingual interpretation.

    Args:
        locale: "ru" or "en". Filters which interpretation field is surfaced.
    """
    path = _KB_DIR / "symbols.json"
    items = []
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data if isinstance(data, list) else data.get("symbols", [])
        for item in raw:
            items.append(
                {
                    "symbol": item.get("symbol") or item.get("name") or item.get("id"),
                    "category": item.get("category"),
                    "archetype": item.get("archetype"),
                    "interpretation": item.get(f"interpretation_{locale}")
                    or item.get("interpretation")
                    or item.get("interpretation_en"),
                }
            )
    return {
        "items": items,
        "source": "backend/services/dreams/knowledge_base/symbols.json (confidence 0.8)",
        "disclaimer": _disclaimer(locale),
    }


def list_archetypes(locale: str = "ru") -> dict[str, Any]:
    """List Jungian archetypes used by the dream interpreter.

    Returns: shadow, anima, animus, self, hero, transformation, persona,
    trickster, mother, father, child, wise_old_man. Used as a vocabulary
    when reading `analyze_dream` results.
    """
    return {
        "items": [
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
        ],
        "source": "Jung, C.G. — archetype vocabulary of the dream KB",
        "disclaimer": _disclaimer(locale),
    }


def list_hvdc_categories(locale: str = "ru") -> dict[str, Any]:
    """List Hall/Van de Castle content analysis categories.

    Reference: Hall & Van de Castle, *The Content Analysis of Dreams* (1966).
    """
    return {
        "items": [c.value for c in DreamCategory],
        "source": "Hall & Van de Castle (1966), The Content Analysis of Dreams",
        "disclaimer": _disclaimer(locale),
    }
