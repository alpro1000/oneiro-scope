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

    # Emotion intensity calculation constants
    EMOTION_INTENSITY_AMPLIFIER = 10.0  # Amplifies emotion density to 0-1 scale
    EMOTION_INTENSITY_MIN = 0.3  # Minimum baseline intensity for detected emotions
    EMOTION_INTENSITY_NEUTRAL = 0.3  # Default intensity for neutral emotions

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
                # Build flexible pattern supporting Russian word forms
                # For Russian words (Cyrillic), match word roots without strict boundaries
                pattern_parts = []
                for kw in keywords:
                    escaped_kw = re.escape(kw)
                    # Check if keyword contains Cyrillic characters
                    if re.search(r'[а-яА-ЯёЁ]', kw):
                        # Russian word: match root + any ending (handles inflections)
                        # E.g., "машина" matches "машины", "машину", "машине"
                        pattern_parts.append(rf'\b{escaped_kw}\w*\b')
                    else:
                        # English word: exact match with word boundaries
                        pattern_parts.append(rf'\b{escaped_kw}\b')

                pattern = '(' + '|'.join(pattern_parts) + ')'
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
                r'\b(help|friend|together|support|kindness|'
                r'помочь|друг|вместе|поддержка|доброта)\b',
                re.IGNORECASE
            ),
            "aggressive": re.compile(
                r'\b(fight|attack|hit|kill|angry|chase|'
                r'драка|атака|ударить|убить|злой|погоня)\b',
                re.IGNORECASE
            ),
            "sexual": re.compile(
                r'\b(kiss|hug|embrace|love|romance|intimacy|intimate|caress|passion|'
                r'flirt|seduce|lover|romantic|attraction|desire|'
                r'поцелуй|целовать|обнимать|объятия|любовь|романтика|интимность|'
                r'ласка|страсть|флирт|соблазн|возлюбленн|романтичн|влечение|желание)\b',
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
        """
        Find and interpret symbols in dream text with contextual validation.

        Uses narrative-first approach: symbols are only included if they
        appear in appropriate semantic context (v2.1).
        """
        found_symbols = []
        text_lower = text.lower()

        for symbol_id, symbol_data in self.symbol_patterns.items():
            matches = symbol_data["pattern"].findall(text_lower)
            if matches:
                # Contextual validation (v2.1 feature)
                if self._validate_symbol_context(symbol_id, text_lower, matches):
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

    def _validate_symbol_context(self, symbol_id: str, text: str, matches: List[str]) -> bool:
        """
        Validate that detected symbol appears in appropriate context (v2.1).

        Prevents false positives like:
        - "house" symbol from "car door" (door keyword)
        - "food" symbol from "food truck" when truck is the focus

        Args:
            symbol_id: Symbol identifier (e.g., "house", "vehicle")
            text: Full dream text (lowercased)
            matches: List of matched keywords

        Returns:
            True if symbol is contextually valid, False otherwise
        """
        # Context exclusion rules (prevent false positives)
        exclusion_contexts = {
            "house": [
                # "door" in "car/machine door" context → exclude house symbol
                # Using flexible matching for Russian inflections
                (r'(car|vehicle|auto|машин|автомобил).{0,10}(door|дверь)', ["door", "дверь"]),
                # "window" in "car window" → exclude house
                (r'(car|vehicle|auto|машин|автомобил).{0,10}(window|окн)', ["window", "окно", "окна"]),
                # Reverse: "door/window of car"
                (r'(door|дверь).{0,10}(car|vehicle|машин|автомобил)', ["door", "дверь"]),
                (r'(window|окн).{0,10}(car|vehicle|машин|автомобил)', ["window", "окно", "окна"]),
            ],
            "food": [
                # "food" in "food truck" when vehicle is focus → exclude food
                (r'food\s+truck', ["food"]),
                # Common false positives where food is mentioned but not central
                (r'(без|without).{0,10}(food|еда)', ["food", "еда"]),
            ],
            "water": [
                # "water" in "watermark" or "waterproof" → exclude
                (r'water(mark|proof)', ["water"]),
            ],
        }

        # Check if any matched keyword appears in exclusion context
        if symbol_id in exclusion_contexts:
            for pattern_str, excluded_keywords in exclusion_contexts[symbol_id]:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                if pattern.search(text):
                    # Check if the matched keyword is one that should be excluded
                    for match in matches:
                        if match.lower() in [k.lower() for k in excluded_keywords]:
                            return False  # Found in exclusion context

        # Context reinforcement rules (boost confidence for good contexts)
        # Using word roots for Russian to match inflections
        reinforcement_contexts = {
            "surveillance": [
                # Strong indicators that surveillance is real theme
                r'(track|monitor|watch|follow|spy|след|наблюд|контрол)',
            ],
            "boundaries": [
                r'(violat|invad|cross|breach|нарушен|вторжен|пересеч|границ)',
            ],
            "control": [
                r'(manipulat|dominat|power|restrict|манипул|доминир|власть|огранич)',
            ],
            "escape_liberation": [
                # Match roots: выброс/выбросил, отброс/отбросил, освобод/освободился
                r'(throw\s+away|discard|reject|break\s+free|выброс|отброс|освобод|свобод)',
            ],
        }

        # For symbols with reinforcement patterns, check for supporting context
        # Note: This is a SOFT filter - we don't block symbols entirely,
        # just note their confidence. LLM will make final validation.
        if symbol_id in reinforcement_contexts:
            has_reinforcement = False
            for pattern_str in reinforcement_contexts[symbol_id]:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                if pattern.search(text):
                    has_reinforcement = True
                    break

            # Even without reinforcement, allow symbol through
            # The LLM will do final contextual validation
            # This prevents over-filtering at the regex level
            return True  # Changed from: return has_reinforcement

        # Default: symbol is valid (conservative approach)
        return True

    def _analyze_content(self, text: str) -> ContentAnalysis:
        """Perform Hall/Van de Castle content analysis"""

        # Character counts
        male_chars = len(self.character_patterns["male"].findall(text))
        female_chars = len(self.character_patterns["female"].findall(text))
        animal_chars = len(self.character_patterns["animal"].findall(text))

        # Interaction types
        friendly = len(self.interaction_patterns["friendly"].findall(text))
        aggressive = len(self.interaction_patterns["aggressive"].findall(text))
        sexual = len(self.interaction_patterns["sexual"].findall(text))

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
            sexual_interactions=sexual,  # Keyword-based detection (H/VdC methodology)
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
        """Determine primary emotion and intensity using knowledge base"""
        text_lower = text.lower()

        emotion_counts = {
            EmotionType.HAPPINESS: 0,
            EmotionType.SADNESS: 0,
            EmotionType.ANGER: 0,
            EmotionType.APPREHENSION: 0,
            EmotionType.CONFUSION: 0,
        }

        # Load emotion words from knowledge base
        emotion_types = self.knowledge_base.get("emotions", {}).get("by_type", {})

        # Count emotion indicators from knowledge base
        happiness_words = emotion_types.get("happiness", [])
        for word in happiness_words:
            if word in text_lower:
                emotion_counts[EmotionType.HAPPINESS] += 1

        sadness_words = emotion_types.get("sadness", [])
        for word in sadness_words:
            if word in text_lower:
                emotion_counts[EmotionType.SADNESS] += 1

        anger_words = emotion_types.get("anger", [])
        for word in anger_words:
            if word in text_lower:
                emotion_counts[EmotionType.ANGER] += 1

        # Fear/apprehension indicators
        fear_words = emotion_types.get("fear", [])
        for word in fear_words:
            if word in text_lower:
                emotion_counts[EmotionType.APPREHENSION] += 1

        confusion_words = emotion_types.get("confusion", [])
        for word in confusion_words:
            if word in text_lower:
                emotion_counts[EmotionType.CONFUSION] += 1

        # Find primary emotion
        max_count = max(emotion_counts.values())
        if max_count == 0:
            return EmotionType.NEUTRAL, self.EMOTION_INTENSITY_NEUTRAL

        primary = max(emotion_counts.items(), key=lambda x: x[1])[0]

        # Calculate intensity (normalized to 0-1 scale)
        # Formula: (emotion_word_count / total_words) * amplifier
        # Amplifier converts typical emotion density (1-5%) to 0.1-0.5 range
        word_count = len(text.split())
        emotion_density = max_count / max(1, word_count)
        intensity = min(1.0, emotion_density * self.EMOTION_INTENSITY_AMPLIFIER)
        intensity = max(self.EMOTION_INTENSITY_MIN, intensity)  # Apply minimum threshold

        return primary, intensity

    def _extract_themes(
        self,
        symbols: List[DreamSymbol],
        content: ContentAnalysis,
        locale: str
    ) -> List[str]:
        """Extract main themes from analysis using knowledge base"""
        themes = []

        # Load theme translations from knowledge base
        theme_data = self.knowledge_base.get("themes", {})

        # Helper to get localized theme text
        def get_theme(theme_key: str) -> str:
            theme_entry = theme_data.get(theme_key, {})
            return theme_entry.get(locale, theme_entry.get("en", theme_key))

        # Analyze symbols for themes
        symbol_ids = [s.symbol for s in symbols]

        if "flying" in symbol_ids:
            themes.append(get_theme("freedom"))
        if "death" in symbol_ids or "water" in symbol_ids:
            themes.append(get_theme("transformation"))
        if content.friendly_interactions > 0 or content.female_characters + content.male_characters > 2:
            themes.append(get_theme("relationships"))
        if "chase" in symbol_ids or "falling" in symbol_ids:
            themes.append(get_theme("anxiety"))
        if "house" in symbol_ids or "naked" in symbol_ids:
            themes.append(get_theme("self_discovery"))
        if content.aggressive_interactions > content.friendly_interactions:
            themes.append(get_theme("conflict"))
        if content.successes > content.failures:
            themes.append(get_theme("success"))
        if content.failures > content.successes:
            themes.append(get_theme("loss"))

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
