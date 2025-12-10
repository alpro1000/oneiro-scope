"""
Dream AI Interpreter

Uses multiple LLM providers for generating meaningful dream interpretations
based on analyzed content and scientific methodology.
"""

from typing import List, Optional

from backend.core.llm_provider import UniversalLLMProvider, LLMProvider
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
        locale: str = "ru",
    ) -> tuple[str, str, List[str]]:
        """
        Generate AI interpretation of the dream.

        Returns:
            - Summary (brief)
            - Full interpretation
            - Recommendations
        """
        try:
            return await self._call_llm(
                dream_text, symbols, content, emotion, emotion_intensity,
                themes, archetypes, lunar_context, locale
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
        locale: str,
    ) -> tuple[str, str, List[str]]:
        """Call LLM provider for interpretation"""

        system_prompt = self._build_system_prompt(locale)
        user_prompt = self._build_user_prompt(
            dream_text, symbols, content, emotion, emotion_intensity,
            themes, archetypes, lunar_context, locale
        )

        # Use universal LLM provider
        response_text, provider = await self.llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        return self._parse_response(response_text, locale)

    def _build_system_prompt(self, locale: str) -> str:
        """Build system prompt for Claude"""
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
{lunar_info}

Дай интерпретацию в указанном формате."""

        return f"""Analyze this dream:

DREAM: {dream_text}

FOUND SYMBOLS:
{symbol_info}

CONTENT ANALYSIS:
{content_info}

PRIMARY EMOTION: {emotion.value} (intensity: {emotion_intensity:.1f})
THEMES: {', '.join(themes) if themes else 'not identified'}
ARCHETYPES: {', '.join(archetypes) if archetypes else 'not identified'}
{lunar_info}

Provide interpretation in the specified format."""

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
