"""
Dream Analysis Service

Main service orchestrating dream analysis using scientific methodology.
"""

import uuid
from datetime import datetime, date
from typing import Optional

from backend.services.dreams.schemas import (
    DreamAnalysisRequest,
    DreamAnalysisResponse,
    LunarContext,
)
from backend.services.dreams.analyzer import DreamAnalyzer
from backend.services.dreams.ai.interpreter import DreamInterpreter


class DreamService:
    """
    Main dream analysis service.

    Combines:
    - Hall/Van de Castle content analysis
    - Symbol recognition from knowledge base
    - AI-powered interpretation
    - Lunar calendar context
    """

    def __init__(self):
        self.analyzer = DreamAnalyzer()
        self.interpreter = DreamInterpreter()

    async def analyze_dream(
        self,
        request: DreamAnalysisRequest,
    ) -> DreamAnalysisResponse:
        """
        Perform complete dream analysis.

        Steps:
        1. Content analysis (Hall/Van de Castle)
        2. Symbol recognition
        3. Emotion detection
        4. Lunar context (if date provided)
        5. AI interpretation
        """

        # Step 1-4: Analyze dream content
        symbols, content, emotion, intensity, themes, archetypes = self.analyzer.analyze(
            request.dream_text,
            request.locale,
        )

        # Step 5: Get lunar context if date provided
        lunar_context = None
        if request.dream_date:
            lunar_context = await self._get_lunar_context(
                request.dream_date,
                request.locale,
            )

        # Step 6: Generate AI interpretation
        summary, interpretation, recommendations = await self.interpreter.generate_interpretation(
            dream_text=request.dream_text,
            symbols=symbols,
            content=content,
            emotion=emotion,
            emotion_intensity=intensity,
            themes=themes,
            archetypes=archetypes,
            lunar_context=lunar_context,
            locale=request.locale,
        )

        # Build response
        return DreamAnalysisResponse(
            status="success",
            dream_id=f"dream_{uuid.uuid4().hex[:12]}",
            analyzed_at=datetime.utcnow(),
            word_count=self.analyzer.get_word_count(request.dream_text),
            primary_emotion=emotion,
            emotion_intensity=intensity,
            symbols=symbols,
            content_analysis=content,
            lunar_context=lunar_context,
            summary=summary,
            interpretation=interpretation,
            themes=themes,
            archetypes=archetypes,
            recommendations=recommendations,
        )

    async def _get_lunar_context(
        self,
        dream_date: date,
        locale: str,
    ) -> Optional[LunarContext]:
        """Get lunar context for dream date"""
        try:
            # Import lunar service
            from backend.services.lunar.lunar_service import LunarService

            lunar_service = LunarService()
            lunar_data = lunar_service.get_lunar_day(dream_date)

            # Lunar day interpretations for dreams
            lunar_dream_meanings = self._get_lunar_dream_meaning(
                lunar_data.lunar_day,
                lunar_data.moon_phase,
                locale,
            )

            return LunarContext(
                lunar_day=lunar_data.lunar_day,
                lunar_phase=lunar_data.moon_phase,
                moon_sign=lunar_data.moon_zodiac,
                interpretation_ru=lunar_dream_meanings["ru"],
                interpretation_en=lunar_dream_meanings["en"],
            )
        except Exception:
            return None

    def _get_lunar_dream_meaning(
        self,
        lunar_day: int,
        moon_phase: str,
        locale: str,
    ) -> dict:
        """Get dream significance based on lunar day"""

        # Simplified lunar dream meanings
        meanings = {
            # New Moon (1-3)
            (1, 3): {
                "ru": "Сны в период новолуния часто указывают на новые начинания и скрытые желания. Обратите внимание на символы, связанные с зарождением.",
                "en": "Dreams during new moon often indicate new beginnings and hidden desires. Pay attention to symbols related to birth and creation.",
            },
            # Waxing (4-13)
            (4, 13): {
                "ru": "Сны на растущей Луне обычно связаны с ростом, развитием и накоплением энергии. Хорошее время для анализа целей.",
                "en": "Dreams during waxing moon are typically about growth, development, and energy accumulation. Good time to analyze goals.",
            },
            # Full Moon (14-16)
            (14, 16): {
                "ru": "Полнолуние усиливает яркость и эмоциональность снов. Сны в это время особенно значимы и часто пророческие.",
                "en": "Full moon enhances dream vividness and emotionality. Dreams during this time are particularly significant and often prophetic.",
            },
            # Waning (17-28)
            (17, 28): {
                "ru": "Сны на убывающей Луне часто связаны с завершением циклов, отпусканием и очищением. Время для избавления от старого.",
                "en": "Dreams during waning moon often relate to cycle completion, letting go, and cleansing. Time for releasing the old.",
            },
            # Dark Moon (29-30)
            (29, 30): {
                "ru": "Сны в тёмную Луну могут быть особенно глубокими и символичными. Время для внутренней работы и самоанализа.",
                "en": "Dreams during dark moon can be especially deep and symbolic. Time for inner work and self-reflection.",
            },
        }

        for (start, end), meaning in meanings.items():
            if start <= lunar_day <= end:
                return meaning

        # Default
        return {
            "ru": "Лунный день влияет на содержание и значимость снов.",
            "en": "The lunar day affects dream content and significance.",
        }
