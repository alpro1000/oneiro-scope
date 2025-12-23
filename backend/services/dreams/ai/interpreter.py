"""
Dream AI Interpreter

Uses multiple LLM providers for generating meaningful dream interpretations
based on analyzed content and scientific methodology.

Features:
- Automatic language detection (RU/EN)
- JSON-based bilingual prompts
- Hall/Van de Castle norm comparison
- Jungian archetypal analysis
"""

import json
import re
import logging
from pathlib import Path
from typing import List, Optional

from backend.core.llm_provider import UniversalLLMProvider, LLMProvider

logger = logging.getLogger(__name__)
from backend.services.dreams.schemas import (
    DreamSymbol,
    ContentAnalysis,
    EmotionType,
    LunarContext,
)


class DreamInterpreter:
    """
    AI-powered dream interpreter using multiple LLM providers.

    Generates interpretations based on:
    - Hall/Van de Castle content analysis
    - Found symbols and archetypes
    - Lunar context
    - Scientific dream research
    """

    def __init__(
        self,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        preferred_provider: Optional[LLMProvider] = None,
    ):
        """
        Initialize DreamInterpreter.

        Args:
            max_tokens: Maximum tokens for response
            temperature: Temperature for generation (0.0-1.0)
            preferred_provider: Preferred LLM provider (or None for cheapest)
        """
        self.llm = UniversalLLMProvider(
            max_tokens=max_tokens,
            temperature=temperature,
            preferred_provider=preferred_provider,
        )

        # Path to prompts directory
        self._prompts_dir = Path(__file__).parent / "prompts"

    def _detect_language(self, text: str) -> str:
        """
        Detect dream text language (ru/en) using letter statistics.

        Uses simple heuristics robust to mixed-language texts.

        Args:
            text: Dream text to analyze

        Returns:
            'ru' or 'en'
        """
        if not text or len(text.strip()) < 10:
            return "ru"  # default

        # Count Cyrillic and Latin letters
        cyr = len(re.findall(r"[а-яА-ЯёЁ]", text))
        lat = len(re.findall(r"[a-zA-Z]", text))

        # Detection logic
        if cyr > lat * 1.5:
            detected = "ru"
        elif lat > cyr * 1.5:
            detected = "en"
        else:
            # Mixed or unclear → default to Russian
            detected = "ru"

        logger.debug(f"Language detection: cyr={cyr}, lat={lat}, detected={detected}")
        return detected

    def _preprocess_dream_text(self, text: str) -> str:
        """
        Preprocess dream text before analysis.

        - Removes excessive repeated characters ("ссссон" → "сон")
        - Normalizes whitespace
        - Removes control characters

        Args:
            text: Raw dream text

        Returns:
            Cleaned dream text
        """
        if not text:
            return ""

        # Remove control characters (except newlines and tabs)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # Reduce repeated characters (3+ same chars → 2)
        text = re.sub(r'(.)\1{2,}', r'\1\1', text)

        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    async def generate_interpretation(
        self,
        dream_text: str,
        symbols: List[DreamSymbol],
        content: ContentAnalysis,
        emotion: EmotionType,
        emotion_intensity: float,
        themes: List[str],
        archetypes: List[str],
        lunar_context: Optional[LunarContext],
        norm_context: Optional[str] = None,
        locale: str = "ru",
    ) -> tuple[str, str, List[str]]:
        """
        Generate AI interpretation of the dream.

        Args:
            norm_context: Optional text describing deviations from Hall/Van de Castle norms

        Returns:
            - Summary (brief)
            - Full interpretation
            - Recommendations
        """
        try:
            return await self._call_llm(
                dream_text, symbols, content, emotion, emotion_intensity,
                themes, archetypes, lunar_context, norm_context, locale
            )
        except Exception as e:
            # Fallback on API error
            return self._generate_fallback(
                symbols, content, emotion, themes, archetypes, lunar_context, locale
            )

    async def _call_llm(
        self,
        dream_text: str,
        symbols: List[DreamSymbol],
        content: ContentAnalysis,
        emotion: EmotionType,
        emotion_intensity: float,
        themes: List[str],
        archetypes: List[str],
        lunar_context: Optional[LunarContext],
        norm_context: Optional[str],
        locale: str,
    ) -> tuple[str, str, List[str]]:
        """Call LLM provider for interpretation"""

        # Preprocess dream text
        clean_dream = self._preprocess_dream_text(dream_text)

        # Build prompts with auto-detection
        system_prompt = self._build_system_prompt(locale, dream_text=clean_dream)
        user_prompt = self._build_user_prompt(
            dream_text, symbols, content, emotion, emotion_intensity,
            themes, archetypes, lunar_context, norm_context, locale
        )

        # Use universal LLM provider
        response_text, provider = await self.llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        return self._parse_response(response_text, locale)

    def _build_system_prompt(self, locale: str, dream_text: Optional[str] = None) -> str:
        """
        Build system prompt for LLM with auto-detection support.

        Args:
            locale: Explicit locale ('ru' or 'en') or None for auto-detection
            dream_text: Dream text for language detection (optional)

        Returns:
            System prompt string
        """
        # Auto-detect language if dream_text provided and locale seems wrong
        if dream_text:
            detected = self._detect_language(dream_text)
            # Only override if explicit locale doesn't match detected
            if locale not in ("ru", "en"):
                locale = detected
            logger.debug(f"Using locale: {locale} (detected: {detected})")

        # Try JSON-based prompt first
        prompt_file = self._prompts_dir / "dream_interpreter_system.json"
        if prompt_file.exists():
            try:
                return self._build_system_prompt_from_json(prompt_file, locale)
            except Exception as e:
                logger.warning(f"Failed to load JSON prompt: {e}, using fallback")

        # Fallback to inline prompts
        return self._build_system_prompt_inline(locale)

    def _build_system_prompt_from_json(self, prompt_file: Path, locale: str) -> str:
        """Build system prompt from JSON file."""
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_data = json.load(f)

        lang = "ru" if locale == "ru" else "en"

        # Parse style (handle both old string format and new dict format)
        style_data = prompt_data["style"].get(lang)
        if isinstance(style_data, dict):
            # New format (v2.1+): extract readable instructions
            style_parts = []
            if "tone" in style_data:
                style_parts.append(f"Tone: {style_data['tone']}")
            if "language" in style_data:
                style_parts.append(style_data["language"])
            if "prohibited" in style_data:
                prohibited_list = ", ".join(style_data["prohibited"])
                prohib_text = "Prohibited" if lang == "en" else "Запрещено"
                style_parts.append(f"{prohib_text}: {prohibited_list}")
            if "confidence" in style_data:
                style_parts.append(style_data["confidence"])
            style_text = " ".join(style_parts)
        else:
            # Old format (v2.0): direct string
            style_text = style_data

        # Build structured context
        system_context = {
            "role": prompt_data.get("role", "scientific_dream_interpreter"),
            "description": prompt_data.get("description"),
            "version": prompt_data.get("version"),
            "objective": prompt_data["objectives"].get(lang),
            "methodology": prompt_data.get("methodology"),
            "stages": {
                "validation_normalization": prompt_data["stages"]["1_validation_normalization"].get(lang),
                "emotional_analysis": prompt_data["stages"]["2_emotional_analysis"].get(lang),
                "symbolic_archetypal_analysis": prompt_data["stages"]["3_symbolic_archetypal_analysis"].get(lang),
                "interpretation": prompt_data["stages"]["4_interpretation"].get(lang)
            },
            "output_format": prompt_data["output_format"],
            "style": style_text,
            "notes": prompt_data["notes"].get(lang)
        }

        # Add response format instructions
        if lang == "ru":
            format_instructions = """

Формат ответа:
РЕЗЮМЕ: [1-2 предложения]
ИНТЕРПРЕТАЦИЯ: [подробный анализ 3-5 абзацев]
РЕКОМЕНДАЦИИ:
- Рекомендация 1
- Рекомендация 2
- Рекомендация 3"""
        else:
            format_instructions = """

Response format:
SUMMARY: [1-2 sentences]
INTERPRETATION: [detailed analysis 3-5 paragraphs]
RECOMMENDATIONS:
- Recommendation 1
- Recommendation 2
- Recommendation 3"""

        return self._format_system_context_as_text(system_context, lang) + format_instructions

    def _format_system_context_as_text(self, context: dict, lang: str) -> str:
        """Convert system context dict to readable plain text prompt."""
        lines = []

        # Role and description
        lines.append(f"Role: {context.get('role', 'dream_interpreter')}")
        if context.get('description'):
            lines.append(f"Description: {context['description']}")
        if context.get('version'):
            lines.append(f"Version: {context['version']}")
        lines.append("")

        # Objective
        if context.get('objective'):
            lines.append("OBJECTIVE:")
            lines.append(context['objective'])
            lines.append("")

        # Methodology
        if context.get('methodology'):
            lines.append("METHODOLOGY:")
            for method in context['methodology']:
                lines.append(f"• {method}")
            lines.append("")

        # Stages
        if context.get('stages'):
            if lang == "ru":
                lines.append("ЭТАПЫ АНАЛИЗА:")
            else:
                lines.append("ANALYSIS STAGES:")

            for stage_key, stage_text in context['stages'].items():
                stage_num = stage_key.split('_')[0] if '_' in stage_key else stage_key
                if isinstance(stage_text, list):
                    # Array format (v2.1 validation)
                    lines.append(f"{stage_num}. {stage_key.replace('_', ' ').title()}:")
                    for step in stage_text:
                        lines.append(f"   • {step}")
                else:
                    # String format
                    lines.append(f"{stage_num}. {stage_text}")
            lines.append("")

        # Style
        if context.get('style'):
            if lang == "ru":
                lines.append("СТИЛЬ:")
            else:
                lines.append("STYLE:")
            lines.append(context['style'])
            lines.append("")

        # Notes
        if context.get('notes'):
            if lang == "ru":
                lines.append("ВАЖНЫЕ ЗАМЕЧАНИЯ:")
            else:
                lines.append("IMPORTANT NOTES:")
            lines.append(context['notes'])
            lines.append("")

        return "\n".join(lines)

    def _build_system_prompt_inline(self, locale: str) -> str:
        """Build inline system prompt (fallback)."""
        if locale == "ru":
            return """Ты — научный интерпретатор снов, использующий методологию Hall/Van de Castle и базу DreamBank.

Твоя задача — давать глубокие, но практичные интерпретации снов на основе:
1. Контент-анализа по системе Hall/Van de Castle
2. Юнгианских архетипов
3. Современных исследований сновидений
4. Лунного контекста (если предоставлен)

Формат ответа:
РЕЗЮМЕ: [1-2 предложения]
ИНТЕРПРЕТАЦИЯ: [подробный анализ 3-5 абзацев]
РЕКОМЕНДАЦИИ:
- Рекомендация 1
- Рекомендация 2
- Рекомендация 3

Будь эмпатичен, но научен. Избегай категоричных утверждений — сны многозначны."""

        return """You are a scientific dream interpreter using Hall/Van de Castle methodology and DreamBank research.

Your task is to provide deep but practical dream interpretations based on:
1. Hall/Van de Castle content analysis
2. Jungian archetypes
3. Modern dream research
4. Lunar context (if provided)

Response format:
SUMMARY: [1-2 sentences]
INTERPRETATION: [detailed analysis 3-5 paragraphs]
RECOMMENDATIONS:
- Recommendation 1
- Recommendation 2
- Recommendation 3

Be empathetic but scientific. Avoid categorical statements — dreams are multi-layered."""

    def _build_user_prompt(
        self,
        dream_text: str,
        symbols: List[DreamSymbol],
        content: ContentAnalysis,
        emotion: EmotionType,
        emotion_intensity: float,
        themes: List[str],
        archetypes: List[str],
        lunar_context: Optional[LunarContext],
        norm_context: Optional[str],
        locale: str,
    ) -> str:
        """Build user prompt with dream data"""

        symbol_info = "\n".join([
            f"- {s.symbol}: {s.interpretation_ru if locale == 'ru' else s.interpretation_en}"
            for s in symbols[:5]
        ]) or ("Явных символов не найдено" if locale == "ru" else "No explicit symbols found")

        content_info = f"""
Characters: {content.male_characters} male, {content.female_characters} female, {content.animal_characters} animals
Interactions: {content.friendly_interactions} friendly, {content.aggressive_interactions} aggressive
Outcomes: {content.successes} successes, {content.failures} failures
Emotions: {content.positive_emotions} positive, {content.negative_emotions} negative"""

        lunar_info = ""
        if lunar_context:
            if locale == "ru":
                lunar_info = f"\nЛунный контекст: {lunar_context.lunar_day}-й лунный день, фаза: {lunar_context.lunar_phase}"
            else:
                lunar_info = f"\nLunar context: Day {lunar_context.lunar_day}, phase: {lunar_context.lunar_phase}"

        norm_info = ""
        if norm_context:
            if locale == "ru":
                norm_info = f"\n\nСРАВНЕНИЕ С НОРМАМИ (DreamBank):\n{norm_context}"
            else:
                norm_info = f"\n\nNORM COMPARISON (DreamBank):\n{norm_context}"

        if locale == "ru":
            return f"""Проанализируй этот сон:

СОН: {dream_text}

НАЙДЕННЫЕ СИМВОЛЫ:
{symbol_info}

КОНТЕНТ-АНАЛИЗ:
{content_info}

ОСНОВНАЯ ЭМОЦИЯ: {emotion.value} (интенсивность: {emotion_intensity:.1f})
ТЕМЫ: {', '.join(themes) if themes else 'не определены'}
АРХЕТИПЫ: {', '.join(archetypes) if archetypes else 'не определены'}
{lunar_info}{norm_info}

Дай интерпретацию в указанном формате. Если есть отклонения от норм, учти их в анализе."""

        return f"""Analyze this dream:

DREAM: {dream_text}

FOUND SYMBOLS:
{symbol_info}

CONTENT ANALYSIS:
{content_info}

PRIMARY EMOTION: {emotion.value} (intensity: {emotion_intensity:.1f})
THEMES: {', '.join(themes) if themes else 'not identified'}
ARCHETYPES: {', '.join(archetypes) if archetypes else 'not identified'}
{lunar_info}{norm_info}

Provide interpretation in the specified format. If there are deviations from norms, incorporate them into your analysis."""

    def _parse_response(self, text: str, locale: str) -> tuple[str, str, List[str]]:
        """Parse Claude's response into components"""
        summary = ""
        interpretation = ""
        recommendations = []

        lines = text.strip().split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            upper = line.upper()
            if upper.startswith("SUMMARY:") or upper.startswith("РЕЗЮМЕ:"):
                current_section = "summary"
                summary = line.split(":", 1)[1].strip() if ":" in line else ""
            elif upper.startswith("INTERPRETATION:") or upper.startswith("ИНТЕРПРЕТАЦИЯ:"):
                current_section = "interpretation"
                interpretation = line.split(":", 1)[1].strip() if ":" in line else ""
            elif upper.startswith("RECOMMENDATIONS:") or upper.startswith("РЕКОМЕНДАЦИИ:"):
                current_section = "recommendations"
            elif current_section == "summary":
                summary += " " + line
            elif current_section == "interpretation":
                interpretation += " " + line
            elif current_section == "recommendations" and line.startswith("-"):
                recommendations.append(line[1:].strip())

        return summary.strip(), interpretation.strip(), recommendations

    def _generate_fallback(
        self,
        symbols: List[DreamSymbol],
        content: ContentAnalysis,
        emotion: EmotionType,
        themes: List[str],
        archetypes: List[str],
        lunar_context: Optional[LunarContext],
        locale: str,
    ) -> tuple[str, str, List[str]]:
        """Generate fallback interpretation without API"""

        if locale == "ru":
            # Summary
            if symbols:
                main_symbol = symbols[0]
                summary = f"Ваш сон содержит значимый символ «{main_symbol.symbol}», связанный с {main_symbol.archetype or 'важными жизненными процессами'}."
            else:
                summary = "Ваш сон отражает текущие эмоциональные процессы и требует внимательного осмысления."

            # Interpretation
            parts = []
            if symbols:
                parts.append("Анализ символов:")
                for s in symbols[:3]:
                    parts.append(f"• {s.symbol.capitalize()}: {s.interpretation_ru}")

            if themes:
                parts.append(f"\nОсновные темы сна: {', '.join(themes)}.")

            emotion_map = {
                EmotionType.HAPPINESS: "радость и удовлетворение",
                EmotionType.SADNESS: "грусть и печаль",
                EmotionType.ANGER: "гнев и раздражение",
                EmotionType.APPREHENSION: "тревога и опасения",
                EmotionType.CONFUSION: "смятение и неопределённость",
                EmotionType.NEUTRAL: "нейтральное состояние",
            }
            parts.append(f"\nПреобладающая эмоция: {emotion_map.get(emotion, 'не определена')}.")

            if archetypes:
                parts.append(f"\nПрисутствующие архетипы: {', '.join(archetypes)}.")

            if lunar_context:
                parts.append(f"\n{lunar_context.interpretation_ru}")

            interpretation = "\n".join(parts)

            # Recommendations
            recommendations = [
                "Запишите сон в дневник для отслеживания повторяющихся тем",
                "Обратите внимание на эмоции, которые вызывает сон в бодрствовании",
                "Подумайте, какие события дня могли повлиять на содержание сна",
            ]

        else:
            # English fallback
            if symbols:
                main_symbol = symbols[0]
                summary = f"Your dream contains the significant symbol '{main_symbol.symbol}', associated with {main_symbol.archetype or 'important life processes'}."
            else:
                summary = "Your dream reflects current emotional processes and requires careful reflection."

            parts = []
            if symbols:
                parts.append("Symbol analysis:")
                for s in symbols[:3]:
                    parts.append(f"• {s.symbol.capitalize()}: {s.interpretation_en}")

            if themes:
                parts.append(f"\nMain themes: {', '.join(themes)}.")

            emotion_map = {
                EmotionType.HAPPINESS: "joy and satisfaction",
                EmotionType.SADNESS: "sadness and grief",
                EmotionType.ANGER: "anger and irritation",
                EmotionType.APPREHENSION: "anxiety and apprehension",
                EmotionType.CONFUSION: "confusion and uncertainty",
                EmotionType.NEUTRAL: "neutral state",
            }
            parts.append(f"\nPredominant emotion: {emotion_map.get(emotion, 'not identified')}.")

            if archetypes:
                parts.append(f"\nPresent archetypes: {', '.join(archetypes)}.")

            if lunar_context:
                parts.append(f"\n{lunar_context.interpretation_en}")

            interpretation = "\n".join(parts)

            recommendations = [
                "Record the dream in a journal to track recurring themes",
                "Pay attention to the emotions the dream evokes when awake",
                "Consider what events of the day may have influenced the dream content",
            ]

        return summary, interpretation, recommendations
