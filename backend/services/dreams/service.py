"""
Dream Analysis Service

Main service orchestrating dream analysis using scientific methodology.
Integrates Hall/Van de Castle content analysis with DreamBank normative data.
"""

import os
import uuid
import json
import logging
from datetime import datetime, date
from typing import Optional, Dict
from pathlib import Path

from backend.services.dreams.schemas import (
    DreamAnalysisRequest,
    DreamAnalysisResponse,
    HvdcEvent,
    InsufficientIndicator,
    LunarContext,
    NormComparisonResult,
    NormDeviation,
)
from backend.services.dreams.analyzer import DreamAnalyzer
from backend.services.dreams.ai.interpreter import DreamInterpreter
from backend.services.dreams.dreambank_loader import get_dreambank_loader
from backend.services.strategic.disclaimer import DISCLAIMERS, DISCLAIMER_RU

logger = logging.getLogger(__name__)

# Direct import, no try/except: pyswisseph is a hard dependency. The old
# guarded import pointed at backend.services.lunar.lunar_service — a module
# that does not exist — so lunar_context was silently None on every call
# and nobody noticed for months. Silent fallbacks on data paths are banned
# (conventions.md §12): a missing dependency must fail loudly at startup.
from backend.services.lunar.engine import LunarEngine


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
        self._lunar_meanings = self._load_lunar_meanings()
        logger.info("DreamService initialized with DreamBank norms")

    def _load_lunar_meanings(self) -> Dict:
        """Load lunar dream meanings from the same KB file the analyzer
        already requires — a missing/broken file raises there first, and
        must raise here too rather than degrade to an empty dict."""
        kb_path = Path(__file__).parent / "knowledge_base" / "symbols.json"
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("lunar_dream_meanings", {})

    async def analyze_dream(
        self,
        request: DreamAnalysisRequest,
        interpret: bool = True,
    ) -> DreamAnalysisResponse:
        """
        Perform complete dream analysis.

        Steps:
        1. Content analysis (Hall/Van de Castle, structural coder)
        2. Symbol recognition
        3. Emotion detection
        4. Norm comparison (DreamBank)
        5. Lunar context (if date provided)
        6. AI interpretation — only when `interpret` is True; the MCP path
           passes False because the calling model reads the data itself
           (same policy as calculate_natal_chart, PR #161).
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
            coding,
        ) = self.analyzer.analyze(
            dream_text,
            request.locale,
            request.physiological_events,
        )

        # Explicit degradation ledger (conventions.md §12): a supplementary
        # computation that fails must say so — never a null that reads the
        # same as "not requested" or "nothing found".
        degraded: list[str] = []

        # Step 4: Compare to Hall/Van de Castle norms
        norm_comparison = self._compare_to_norms(
            content=content,
            gender=request.dreamer_gender,
            degraded=degraded,
        )

        # Step 5: Get lunar context if date provided
        lunar_context = None
        if request.dream_date:
            lunar_context = await self._get_lunar_context(
                request.dream_date,
                request.locale,
                degraded=degraded,
            )

        # Step 6: Server-side prose only when asked for (web client without
        # its own model). The MCP path skips this hop entirely.
        summary, interpretation, recommendations = None, None, []
        if interpret:
            norm_context = None
            if norm_comparison:
                norm_context = self.dreambank.get_interpretation_context(
                    norm_comparison,
                    request.locale,
                )
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
                # Честная рамка: наш кодировщик precision-first и недосчитывает
                # против людей-кодировщиков, строивших нормы 1966 года, —
                # сравнение с историческим корпусом смещено вниз по частотам.
                method_note_ru=(
                    "Кодирование детерминированное, precision-first: часть актов "
                    "(жестовое дружелюбие, модальные неудачи) не досчитывается "
                    "относительно ручного кодирования, которым построены нормы "
                    "1947–1950. Индексы надёжнее сравнивать между снами и "
                    "пользователями этой же версии кодировщика, чем напрямую с "
                    "историческим корпусом; отклонение «ниже нормы» может быть "
                    "артефактом недобора."
                ),
                method_note_en=(
                    "Deterministic precision-first coding: some acts (gesture "
                    "friendliness, modal failures) are undercounted relative to "
                    "the human coders behind the 1947–1950 norms. Indices compare "
                    "more reliably across dreams and users coded by this same "
                    "engine version than directly against the historical corpus; "
                    "a below-norm deviation can be an instrument artifact."
                ),
                overall_typicality=norm_comparison.overall_typicality,
                deviations=[
                    NormDeviation(
                        indicator=d.indicator,
                        user_value=d.user_value,
                        norm_value=d.norm_value,
                        deviation=d.deviation,
                        deviation_unit=d.deviation_unit,
                        significance=d.significance,
                        description_ru=d.description_ru,
                        description_en=d.description_en,
                    )
                    for d in norm_comparison.deviations
                ],
                insufficient_data=[
                    InsufficientIndicator(
                        indicator=i.indicator,
                        reason_ru=i.reason_ru,
                        reason_en=i.reason_en,
                    )
                    for i in norm_comparison.insufficient_data
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
            hvdc_evidence=[
                HvdcEvent(
                    category=e.category,
                    subtype=e.subtype,
                    actor=e.actor,
                    target=e.target,
                    evidence=e.evidence,
                    source=e.source,
                )
                for e in coding.events
            ],
            hvdc_coder_version=coding.coder_version,
            lunar_context=lunar_context,
            norm_comparison=norm_result,
            summary=summary,
            interpretation=interpretation,
            themes=themes,
            archetypes=archetypes,
            physiological_correlations=physiological_correlations,
            recommendations=recommendations,
            disclaimer=DISCLAIMERS.get(request.locale, DISCLAIMER_RU),
            degraded=degraded,
        )

    def _compare_to_norms(
        self,
        content,
        gender: Optional[str],
        degraded: Optional[list] = None,
    ):
        """Compare content analysis to Hall/Van de Castle norms.

        A comparison failure lands in `degraded` — a silent None here was
        indistinguishable from «пол не передан»."""
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
            if degraded is not None:
                degraded.append(f"norm_comparison: failed ({e})")
            return None

    async def _get_lunar_context(
        self,
        dream_date: date,
        locale: str,
        degraded: Optional[list] = None,
    ) -> Optional[LunarContext]:
        """Get lunar context for dream date.

        Supplementary computation: a failure does not kill the analysis,
        but it must be VISIBLE — the old silent None here hid a broken
        import for months (the field was null on every call and read the
        same as «дата не передана»)."""
        try:
            timezone = os.getenv("LUNAR_DEFAULT_TZ", "Europe/Moscow")
            lunar_data = LunarEngine().get_lunar_day(dream_date, timezone)

            # Lunar day interpretations for dreams
            lunar_dream_meanings = self._get_lunar_dream_meaning(
                lunar_data["lunar_day"],
                lunar_data["phase"],
                locale,
            )

            return LunarContext(
                lunar_day=lunar_data["lunar_day"],
                lunar_phase=lunar_data["phase"],
                moon_sign=lunar_data.get("moon_sign"),
                interpretation_ru=lunar_dream_meanings["ru"],
                interpretation_en=lunar_dream_meanings["en"],
            )
        except (ValueError, AttributeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to get lunar context: {e}", exc_info=True)
            if degraded is not None:
                degraded.append(f"lunar_context: unavailable ({e})")
            return None

    def _get_lunar_dream_meaning(
        self,
        lunar_day: int,
        moon_phase: str,
        locale: str,
    ) -> dict:
        """Get dream significance based on lunar day from knowledge base"""

        # Find matching lunar phase from knowledge base
        for phase_key, phase_data in self._lunar_meanings.items():
            if phase_key == "default":
                continue

            days = phase_data.get("days", [])
            if lunar_day in days:
                return {
                    "ru": phase_data.get("ru", ""),
                    "en": phase_data.get("en", ""),
                }

        # Fallback to default meaning
        default = self._lunar_meanings.get("default", {})
        return {
            "ru": default.get("ru", "Лунный день влияет на содержание и значимость снов."),
            "en": default.get("en", "The lunar day affects dream content and significance."),
        }
