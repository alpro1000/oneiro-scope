"""
Dream Analysis Service

Main service orchestrating dream analysis using scientific methodology.
Integrates Hall/Van de Castle content analysis with DreamBank normative data.
"""

import uuid
import logging
from datetime import datetime, date
from typing import Optional

from backend.services.dreams.schemas import (
    DreamAnalysisRequest,
    DreamAnalysisResponse,
    LunarContext,
    NormComparisonResult,
    NormDeviation,
)
from backend.services.dreams.analyzer import DreamAnalyzer
from backend.services.dreams.ai.interpreter import DreamInterpreter
from backend.services.dreams.dreambank_loader import get_dreambank_loader

logger = logging.getLogger(__name__)

# Optional lunar service import (graceful degradation if not available)
try:
    from backend.services.lunar.lunar_service import LunarService
    LUNAR_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("LunarService not available, lunar context will be disabled")
    LunarService = None
    LUNAR_SERVICE_AVAILABLE = False


class DreamService:
    """
    Main dream analysis service.

    Combines:
    - Hall/Van de Castle content analysis
    - DreamBank normative data comparison
    - Symbol recognition from knowledge base
    - AI-powered interpretation
    - Lunar calendar context
    """

    def __init__(self):
        self.analyzer = DreamAnalyzer()
        self.interpreter = DreamInterpreter()
        self.dreambank = get_dreambank_loader()
        logger.info("DreamService initialized with DreamBank norms")

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
        4. Norm comparison (DreamBank)
        5. Lunar context (if date provided)
        6. AI interpretation
        """

        # Validate dream text
        dream_text = request.dream_text.strip()

        if not dream_text:
            raise ValueError("Dream text cannot be empty or contain only whitespace")

        if len(dream_text) < 10:
            raise ValueError(
                f"Dream text too short ({len(dream_text)} characters). "
                f"Minimum length is 10 characters for meaningful analysis."
            )

        if len(dream_text) > 10000:
            raise ValueError(
                f"Dream text too long ({len(dream_text)} characters). "
                f"Maximum length is 10,000 characters. Please split into separate dreams."
            )

        # Step 1-3: Analyze dream content (includes physiological correlations)
        (
            symbols,
            content,
            emotion,
            intensity,
            themes,
            archetypes,
            physiological_correlations,
        ) = self.analyzer.analyze(
            dream_text,
            request.locale,
            request.physiological_events,
        )

        # Step 4: Compare to Hall/Van de Castle norms
        norm_comparison = self._compare_to_norms(
            content=content,
            gender=request.dreamer_gender,
        )

        # Step 5: Get lunar context if date provided
        lunar_context = None
        if request.dream_date:
            lunar_context = await self._get_lunar_context(
                request.dream_date,
                request.locale,
            )

        # Get norm context for AI interpretation
        norm_context = None
        if norm_comparison:
            norm_context = self.dreambank.get_interpretation_context(
                norm_comparison,
                request.locale,
            )

        # Step 6: Generate AI interpretation with norm context
        summary, interpretation, recommendations = await self.interpreter.generate_interpretation(
            dream_text=dream_text,
            symbols=symbols,
            content=content,
            emotion=emotion,
            emotion_intensity=intensity,
            themes=themes,
            archetypes=archetypes,
            lunar_context=lunar_context,
            norm_context=norm_context,
            locale=request.locale,
        )

        # Convert norm comparison to Pydantic model
        norm_result = None
        if norm_comparison:
            norm_result = NormComparisonResult(
                gender_used=norm_comparison.gender_used.value,
                overall_typicality=norm_comparison.overall_typicality,
                deviations=[
                    NormDeviation(
                        indicator=d.indicator,
                        user_value=d.user_value,
                        norm_value=d.norm_value,
                        deviation=d.deviation,
                        significance=d.significance,
                        description_ru=d.description_ru,
                        description_en=d.description_en,
                    )
                    for d in norm_comparison.deviations
                ],
                notable_findings_ru=norm_comparison.notable_findings_ru,
                notable_findings_en=norm_comparison.notable_findings_en,
            )

        # Build response
        return DreamAnalysisResponse(
            status="success",
            dream_id=f"dream_{uuid.uuid4().hex[:12]}",
            analyzed_at=datetime.utcnow(),
            word_count=self.analyzer.get_word_count(dream_text),
            primary_emotion=emotion,
            emotion_intensity=intensity,
            symbols=symbols,
            content_analysis=content,
            lunar_context=lunar_context,
            norm_comparison=norm_result,
            summary=summary,
            interpretation=interpretation,
            themes=themes,
            archetypes=archetypes,
            physiological_correlations=physiological_correlations,
            recommendations=recommendations,
        )

    def _compare_to_norms(
        self,
        content,
        gender: Optional[str],
    ):
        """Compare content analysis to Hall/Van de Castle norms"""
        try:
            content_dict = {
                "male_characters": content.male_characters,
                "female_characters": content.female_characters,
                "animal_characters": content.animal_characters,
                "friendly_interactions": content.friendly_interactions,
                "aggressive_interactions": content.aggressive_interactions,
                "successes": content.successes,
                "failures": content.failures,
                "positive_emotions": content.positive_emotions,
                "negative_emotions": content.negative_emotions,
            }
            return self.dreambank.compare_to_norms(content_dict, gender)
        except (ValueError, KeyError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to compare to norms: {e}", exc_info=True)
            return None

    async def _get_lunar_context(
        self,
        dream_date: date,
        locale: str,
    ) -> Optional[LunarContext]:
        """Get lunar context for dream date"""
        # Check if lunar service is available
        if not LUNAR_SERVICE_AVAILABLE or LunarService is None:
            logger.debug("Lunar service not available, skipping lunar context")
            return None

        try:
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
        except (ValueError, AttributeError, KeyError, TypeError) as e:
            # Lunar context is optional, log error but continue
            logger.warning(f"Failed to get lunar context: {e}", exc_info=True)
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
