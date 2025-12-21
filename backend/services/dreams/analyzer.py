"""
Dream Content Analyzer

Implements Hall/Van de Castle content analysis methodology
for scientific dream interpretation.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter

from backend.services.dreams.schemas import (
    ContentAnalysis,
    DreamCategory,
    DreamSymbol,
    EmotionType,
    CharacterType,
    PhysiologicalCorrelation,
    PhysiologicalEvent,
)


class DreamAnalyzer:
    """
    Analyzes dream content using Hall/Van de Castle methodology.

    The Hall/Van de Castle system is the most widely used
    scientific method for dream content analysis, developed
    at Case Western Reserve University.
    """

    def __init__(self):
        self.knowledge_base = self._load_knowledge_base()
        self._compile_patterns()

    def _load_knowledge_base(self) -> Dict:
        """Load symbol knowledge base from JSON"""
        kb_path = Path(__file__).parent / "knowledge_base" / "symbols.json"
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"symbols": [], "emotions": {}, "archetypes": {}}

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""
        self.symbol_patterns = {}
        for symbol in self.knowledge_base.get("symbols", []):
            keywords = symbol.get("keywords", [])
            if keywords:
                pattern = r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
                self.symbol_patterns[symbol["id"]] = {
                    "pattern": re.compile(pattern, re.IGNORECASE),
                    "data": symbol
                }

        # Emotion patterns
        self.emotion_patterns = {
            "positive": self.knowledge_base.get("emotions", {}).get("positive", []),
            "negative": self.knowledge_base.get("emotions", {}).get("negative", []),
            "neutral": self.knowledge_base.get("emotions", {}).get("neutral", []),
        }

        # Character patterns
        self.character_patterns = {
            "male": re.compile(
                r'\b(man|men|boy|father|brother|he|him|his|'
                r'мужчина|мужчины|парень|отец|брат|он|его)\b',
                re.IGNORECASE
            ),
            "female": re.compile(
                r'\b(woman|women|girl|mother|sister|she|her|'
                r'женщина|женщины|девушка|мать|сестра|она|её)\b',
                re.IGNORECASE
            ),
            "animal": re.compile(
                r'\b(animal|dog|cat|bird|snake|horse|fish|'
                r'животное|собака|кошка|птица|змея|лошадь|рыба)\b',
                re.IGNORECASE
            ),
        }

        # Interaction patterns
        self.interaction_patterns = {
            "friendly": re.compile(
                r'\b(help|love|hug|kiss|friend|together|'
                r'помочь|любовь|обнять|поцелуй|друг|вместе)\b',
                re.IGNORECASE
            ),
            "aggressive": re.compile(
                r'\b(fight|attack|hit|kill|angry|chase|'
                r'драка|атака|ударить|убить|злой|погоня)\b',
                re.IGNORECASE
            ),
        }

        # Success/failure patterns
        self.outcome_patterns = {
            "success": re.compile(
                r'\b(succeed|win|achieve|accomplish|find|'
                r'успех|победить|достичь|найти|получить)\b',
                re.IGNORECASE
            ),
            "failure": re.compile(
                r'\b(fail|lose|miss|unable|can\'t|cannot|'
                r'провал|проиграть|потерять|не могу|не получается)\b',
                re.IGNORECASE
            ),
        }

    def analyze(
        self,
        dream_text: str,
        locale: str = "ru",
        physiological_events: Optional[List[PhysiologicalEvent]] = None,
    ) -> Tuple[
        List[DreamSymbol],
        ContentAnalysis,
        EmotionType,
        float,
        List[str],
        List[str],
        List[PhysiologicalCorrelation],
    ]:
        """
        Perform full content analysis on dream text.

        Returns:
            - List of found symbols
            - Content analysis statistics
            - Primary emotion
            - Emotion intensity
            - Themes
            - Archetypes
        """
        text_lower = dream_text.lower()

        # Find symbols
        symbols = self._find_symbols(dream_text, locale)

        # Content analysis
        content = self._analyze_content(dream_text)

        # Emotion analysis
        emotion, intensity = self._analyze_emotions(dream_text)

        # Extract themes
        themes = self._extract_themes(symbols, content, locale)

        # Extract archetypes
        archetypes = self._extract_archetypes(symbols)

        physiological_correlations = self._cross_index_physiology(
            archetypes,
            physiological_events,
        )

        return symbols, content, emotion, intensity, themes, archetypes, physiological_correlations

    def _find_symbols(self, text: str, locale: str) -> List[DreamSymbol]:
        """Find and interpret symbols in dream text"""
        found_symbols = []
        text_lower = text.lower()

        for symbol_id, symbol_data in self.symbol_patterns.items():
            matches = symbol_data["pattern"].findall(text_lower)
            if matches:
                data = symbol_data["data"]
                found_symbols.append(DreamSymbol(
                    symbol=symbol_id,
                    category=DreamCategory(data["category"]),
                    frequency=len(matches),
                    significance=data["significance"],
                    interpretation_ru=data["interpretation_ru"],
                    interpretation_en=data["interpretation_en"],
                    archetype=data.get("archetype"),
                ))

        # Sort by significance
        found_symbols.sort(key=lambda s: s.significance, reverse=True)
        return found_symbols

    def _analyze_content(self, text: str) -> ContentAnalysis:
        """Perform Hall/Van de Castle content analysis"""

        # Character counts
        male_chars = len(self.character_patterns["male"].findall(text))
        female_chars = len(self.character_patterns["female"].findall(text))
        animal_chars = len(self.character_patterns["animal"].findall(text))

        # Interaction types
        friendly = len(self.interaction_patterns["friendly"].findall(text))
        aggressive = len(self.interaction_patterns["aggressive"].findall(text))

        # Outcomes
        successes = len(self.outcome_patterns["success"].findall(text))
        failures = len(self.outcome_patterns["failure"].findall(text))

        # Emotions
        positive_count = sum(
            1 for word in self.emotion_patterns["positive"]
            if word.lower() in text.lower()
        )
        negative_count = sum(
            1 for word in self.emotion_patterns["negative"]
            if word.lower() in text.lower()
        )

        # Calculate ratios
        male_female_ratio = None
        if female_chars > 0:
            male_female_ratio = male_chars / female_chars
        elif male_chars > 0:
            male_female_ratio = float(male_chars)

        agg_friend_ratio = None
        if friendly > 0:
            agg_friend_ratio = aggressive / friendly
        elif aggressive > 0:
            agg_friend_ratio = float(aggressive)

        success_fail_ratio = None
        if failures > 0:
            success_fail_ratio = successes / failures
        elif successes > 0:
            success_fail_ratio = float(successes)

        return ContentAnalysis(
            male_characters=male_chars,
            female_characters=female_chars,
            animal_characters=animal_chars,
            friendly_interactions=friendly,
            aggressive_interactions=aggressive,
            sexual_interactions=0,  # Would need explicit detection
            successes=successes,
            failures=failures,
            misfortunes=failures,  # Simplified
            good_fortunes=successes,  # Simplified
            positive_emotions=positive_count,
            negative_emotions=negative_count,
            male_female_ratio=male_female_ratio,
            aggression_friendliness_ratio=agg_friend_ratio,
            success_failure_ratio=success_fail_ratio,
        )

    def _analyze_emotions(self, text: str) -> Tuple[EmotionType, float]:
        """Determine primary emotion and intensity"""
        text_lower = text.lower()

        emotion_counts = {
            EmotionType.HAPPINESS: 0,
            EmotionType.SADNESS: 0,
            EmotionType.ANGER: 0,
            EmotionType.APPREHENSION: 0,
            EmotionType.CONFUSION: 0,
        }

        # Happiness indicators
        happiness_words = ["happy", "joy", "love", "peace", "free", "счастлив", "радость", "любовь", "покой", "свобод"]
        for word in happiness_words:
            if word in text_lower:
                emotion_counts[EmotionType.HAPPINESS] += 1

        # Sadness indicators
        sadness_words = ["sad", "cry", "loss", "alone", "grief", "грустн", "плакать", "потеря", "один", "горе"]
        for word in sadness_words:
            if word in text_lower:
                emotion_counts[EmotionType.SADNESS] += 1

        # Anger indicators
        anger_words = ["angry", "rage", "hate", "fight", "злой", "ярость", "ненавист", "драка"]
        for word in anger_words:
            if word in text_lower:
                emotion_counts[EmotionType.ANGER] += 1

        # Fear/apprehension indicators
        fear_words = ["fear", "afraid", "scary", "terror", "chase", "страх", "боюсь", "страшн", "ужас", "погоня"]
        for word in fear_words:
            if word in text_lower:
                emotion_counts[EmotionType.APPREHENSION] += 1

        # Confusion indicators
        confusion_words = ["confus", "lost", "strange", "weird", "смят", "потерян", "странн"]
        for word in confusion_words:
            if word in text_lower:
                emotion_counts[EmotionType.CONFUSION] += 1

        # Find primary emotion
        max_count = max(emotion_counts.values())
        if max_count == 0:
            return EmotionType.NEUTRAL, 0.3

        primary = max(emotion_counts.items(), key=lambda x: x[1])[0]

        # Calculate intensity (normalized)
        word_count = len(text.split())
        intensity = min(1.0, (max_count / max(1, word_count)) * 10)
        intensity = max(0.3, intensity)  # Minimum threshold

        return primary, intensity

    def _extract_themes(
        self,
        symbols: List[DreamSymbol],
        content: ContentAnalysis,
        locale: str
    ) -> List[str]:
        """Extract main themes from analysis"""
        themes = []

        # Theme mapping
        theme_map = {
            "ru": {
                "freedom": "Свобода и освобождение",
                "transformation": "Трансформация и изменения",
                "relationships": "Отношения и связи",
                "anxiety": "Тревога и страхи",
                "self_discovery": "Самопознание",
                "conflict": "Конфликт и противостояние",
                "success": "Достижения и успех",
                "loss": "Потеря и утрата",
            },
            "en": {
                "freedom": "Freedom and liberation",
                "transformation": "Transformation and change",
                "relationships": "Relationships and connections",
                "anxiety": "Anxiety and fears",
                "self_discovery": "Self-discovery",
                "conflict": "Conflict and confrontation",
                "success": "Achievement and success",
                "loss": "Loss and grief",
            }
        }

        lang = theme_map.get(locale, theme_map["en"])

        # Analyze symbols for themes
        symbol_ids = [s.symbol for s in symbols]

        if "flying" in symbol_ids:
            themes.append(lang["freedom"])
        if "death" in symbol_ids or "water" in symbol_ids:
            themes.append(lang["transformation"])
        if content.friendly_interactions > 0 or content.female_characters + content.male_characters > 2:
            themes.append(lang["relationships"])
        if "chase" in symbol_ids or "falling" in symbol_ids:
            themes.append(lang["anxiety"])
        if "house" in symbol_ids or "naked" in symbol_ids:
            themes.append(lang["self_discovery"])
        if content.aggressive_interactions > content.friendly_interactions:
            themes.append(lang["conflict"])
        if content.successes > content.failures:
            themes.append(lang["success"])
        if content.failures > content.successes:
            themes.append(lang["loss"])

        return themes[:5]  # Limit to top 5 themes

    def _extract_archetypes(self, symbols: List[DreamSymbol]) -> List[str]:
        """Extract Jungian archetypes from symbols"""
        archetypes = []
        seen = set()

        for symbol in symbols:
            if symbol.archetype and symbol.archetype not in seen:
                archetypes.append(symbol.archetype)
                seen.add(symbol.archetype)

        return archetypes

    def _cross_index_physiology(
        self,
        archetypes: List[str],
        physiological_events: Optional[List[PhysiologicalEvent]],
    ) -> List[PhysiologicalCorrelation]:
        """Correlate archetypes with available physiological markers."""

        if not physiological_events:
            return []

        stage_counts = Counter(
            event.sleep_stage for event in physiological_events if event.sleep_stage
        )
        channel_counts = Counter(
            channel
            for event in physiological_events
            for channel in event.channel_names
        )

        correlations: List[PhysiologicalCorrelation] = []
        for archetype in archetypes:
            dominant_stage = [stage_counts.most_common(1)[0][0]] if stage_counts else []
            dominant_channels = [name for name, _ in channel_counts.most_common(3)]
            evidence = len(physiological_events)
            rationale = (
                f"Archetype '{archetype}' co-occurs with {dominant_stage[0] if dominant_stage else 'unspecified stage'} "
                f"and signals across {', '.join(dominant_channels) if dominant_channels else 'unknown channels'}."
            )
            correlations.append(
                PhysiologicalCorrelation(
                    archetype=archetype,
                    sleep_stages=dominant_stage,
                    channel_summary=dominant_channels,
                    evidence_count=evidence,
                    rationale=rationale,
                )
            )

        return correlations

    def get_word_count(self, text: str) -> int:
        """Count words in dream text"""
        return len(text.split())
