"""Dreams API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.services.dreams import (
    DreamService,
    DreamAnalysisRequest,
    DreamAnalysisResponse,
    DreamCategory,
)

router = APIRouter(prefix="/dreams", tags=["dreams"])


def get_dream_service() -> DreamService:
    """Dependency to get dream service instance."""
    return DreamService()


@router.post(
    "/analyze",
    response_model=DreamAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a dream",
    description="""
    Analyze a dream using scientific methodology.

    **Methodology:**
    - Hall/Van de Castle content analysis system
    - DreamBank corpus research
    - Jungian archetype recognition
    - Lunar calendar context

    **Required inputs:**
    - `dream_text`: The dream narrative (10-10000 characters)

    **Optional inputs:**
    - `dream_date`: Date when dream occurred (for lunar context)
    - `dreamer_gender`: For norm comparison
    - `dreamer_age_group`: For norm comparison
    - `locale`: Response language (en/ru)

    **Returns:**
    - Symbol analysis with interpretations
    - Hall/Van de Castle content metrics
    - Primary emotion and intensity
    - Themes and Jungian archetypes
    - AI-generated interpretation
    - Lunar context (if date provided)
    - Practical recommendations

    **Scientific basis:**
    The Hall/Van de Castle system is the most widely used
    quantitative method for dream content analysis,
    developed at Case Western Reserve University.
    """,
)
async def analyze_dream(
    request: DreamAnalysisRequest,
    service: DreamService = Depends(get_dream_service),
) -> DreamAnalysisResponse:
    """Analyze a dream and return interpretation."""
    try:
        return await service.analyze_dream(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze dream: {str(e)}",
        )


@router.get(
    "/categories",
    summary="List dream content categories",
    description="Get list of Hall/Van de Castle content categories used in analysis.",
)
async def list_categories() -> dict:
    """List available dream content categories."""
    category_descriptions = {
        "characters": {
            "en": "People, animals, and creatures in the dream",
            "ru": "Люди, животные и существа во сне",
        },
        "social_interactions": {
            "en": "Interactions between characters (friendly, aggressive, sexual)",
            "ru": "Взаимодействия между персонажами (дружеские, агрессивные, сексуальные)",
        },
        "activities": {
            "en": "Physical and mental activities performed",
            "ru": "Физические и ментальные действия",
        },
        "striving": {
            "en": "Goals, successes, and failures",
            "ru": "Цели, успехи и неудачи",
        },
        "misfortunes": {
            "en": "Negative events and outcomes",
            "ru": "Негативные события и исходы",
        },
        "good_fortunes": {
            "en": "Positive events and outcomes",
            "ru": "Позитивные события и исходы",
        },
        "emotions": {
            "en": "Emotional experiences in the dream",
            "ru": "Эмоциональные переживания во сне",
        },
        "settings": {
            "en": "Locations and environments",
            "ru": "Места и окружение",
        },
        "objects": {
            "en": "Objects and items in the dream",
            "ru": "Предметы и объекты во сне",
        },
        "descriptive_elements": {
            "en": "Modifiers, colors, sizes, etc.",
            "ru": "Модификаторы, цвета, размеры и т.д.",
        },
    }

    return {
        "categories": [
            {
                "value": cat.value,
                "description_en": category_descriptions[cat.value]["en"],
                "description_ru": category_descriptions[cat.value]["ru"],
            }
            for cat in DreamCategory
        ],
        "methodology": "Hall/Van de Castle Content Analysis System",
    }


@router.get(
    "/symbols",
    summary="List common dream symbols",
    description="Get list of common dream symbols with interpretations.",
)
async def list_symbols(
    locale: str = "ru",
) -> dict:
    """List common dream symbols."""
    import json
    from pathlib import Path

    kb_path = Path(__file__).parent.parent.parent / "services" / "dreams" / "knowledge_base" / "symbols.json"

    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        symbols = []
        for s in data.get("symbols", []):
            symbols.append({
                "id": s["id"],
                "category": s["category"],
                "interpretation": s[f"interpretation_{locale}"] if locale in ["ru", "en"] else s["interpretation_en"],
                "archetype": s.get("archetype"),
                "significance": s["significance"],
            })

        return {
            "symbols": symbols,
            "count": len(symbols),
        }
    except FileNotFoundError:
        return {"symbols": [], "count": 0}


@router.get(
    "/archetypes",
    summary="List Jungian archetypes",
    description="Get list of Jungian archetypes used in dream analysis.",
)
async def list_archetypes(
    locale: str = "ru",
) -> dict:
    """List Jungian archetypes."""
    archetypes = [
        {
            "id": "shadow",
            "name_en": "Shadow",
            "name_ru": "Тень",
            "description_en": "The dark, rejected aspects of personality that we don't acknowledge",
            "description_ru": "Тёмные, отвергаемые аспекты личности, которые мы не признаём",
        },
        {
            "id": "anima_animus",
            "name_en": "Anima/Animus",
            "name_ru": "Анима/Анимус",
            "description_en": "The feminine (anima) or masculine (animus) aspect in the unconscious",
            "description_ru": "Женский (анима) или мужской (анимус) аспект в бессознательном",
        },
        {
            "id": "self",
            "name_en": "Self",
            "name_ru": "Самость",
            "description_en": "The unified totality of the psyche, representing wholeness",
            "description_ru": "Объединённая целостность психики, символизирующая полноту",
        },
        {
            "id": "hero",
            "name_en": "Hero",
            "name_ru": "Герой",
            "description_en": "The aspect that overcomes challenges and achieves goals",
            "description_ru": "Аспект, преодолевающий трудности и достигающий целей",
        },
        {
            "id": "transformation",
            "name_en": "Transformation",
            "name_ru": "Трансформация",
            "description_en": "The process of psychological change and growth",
            "description_ru": "Процесс психологического изменения и роста",
        },
        {
            "id": "liberation",
            "name_en": "Liberation",
            "name_ru": "Освобождение",
            "description_en": "Breaking free from limitations and constraints",
            "description_ru": "Освобождение от ограничений и оков",
        },
        {
            "id": "unconscious",
            "name_en": "Unconscious",
            "name_ru": "Бессознательное",
            "description_en": "The hidden depths of the mind, often represented by water",
            "description_ru": "Скрытые глубины разума, часто символизируемые водой",
        },
    ]

    return {
        "archetypes": [
            {
                "id": a["id"],
                "name": a[f"name_{locale}"] if locale in ["ru", "en"] else a["name_en"],
                "description": a[f"description_{locale}"] if locale in ["ru", "en"] else a["description_en"],
            }
            for a in archetypes
        ],
    }
