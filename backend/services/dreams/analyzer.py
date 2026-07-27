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

from backend.services.dreams import morphology
from backend.services.dreams.hvdc_coder import (
    Clause,
    HvdcCoding,
    HvdcCoder,
    get_hvdc_coder,
)
from backend.services.dreams.schemas import (
    ContentAnalysis,
    DreamCategory,
    DreamSymbol,
    EmotionType,
    CharacterType,
    PhysiologicalCorrelation,
    PhysiologicalEvent,
)

# Существительное считается отсутствующим в сцене, когда отрицание стоит
# вплотную («без денег») или в связке с бытийным глаголом («не было воды»).
_EXISTENTIAL_VERBS = {
    "было", "были", "был", "была", "есть", "оказалось", "стало", "будет",
    "was", "were", "is", "are", "be", "been", "had", "have", "has",
}


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
        """Load symbol knowledge base from JSON.

        A missing KB is a broken deployment, not an empty dictionary: the
        old `except FileNotFoundError: return {}` made the analyzer
        silently find zero symbols forever — the exact silent-fallback
        class banned by conventions.md §12."""
        kb_path = Path(__file__).parent / "knowledge_base" / "symbols.json"
        if not kb_path.exists():
            raise RuntimeError(
                f"Dream symbol knowledge base missing: {kb_path}. "
                "The file ships with the repository — a missing KB means a "
                "broken checkout or build, not an empty symbol set."
            )
        with open(kb_path, "r", encoding="utf-8") as f:
            return json.load(f)

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
                    "data": symbol,
                    # Stems of Cyrillic keywords: «змея» and «змею» share
                    # the stem «зме», so inflected Russian dream text still
                    # reaches the symbol when the regex prefix misses.
                    "stems": morphology.keyword_stems(keywords),
                }

        # Emotion patterns
        self.emotion_patterns = {
            "positive": self.knowledge_base.get("emotions", {}).get("positive", []),
            "negative": self.knowledge_base.get("emotions", {}).get("negative", []),
            "neutral": self.knowledge_base.get("emotions", {}).get("neutral", []),
        }

        # Персонажи, взаимодействия и исходы теперь считает структурный
        # кодировщик (hvdc_coder.py) — словарные regex-паттерны для них
        # удалены: подсчёт по ключевым словам давал события без участников
        # и участников без событий.

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
        HvdcCoding,
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
            - Physiological correlations
            - Structural HVdC coding (characters, events, evidence)
        """
        coder = get_hvdc_coder()
        clauses = coder.segment(dream_text)
        coding = coder.code(dream_text, clauses)

        # Find symbols (negation- and context-aware)
        symbols = self._find_symbols(dream_text, locale, coder, clauses)

        # Emotion analysis (negation-aware)
        emotion, intensity = self._analyze_emotions(dream_text, coder, clauses)

        # Content analysis: structural events + emotion word counts
        content = self._analyze_content(dream_text, coding, coder, clauses)

        # Extract themes
        themes = self._extract_themes(symbols, content, locale)

        # Extract archetypes
        archetypes = self._extract_archetypes(symbols)

        physiological_correlations = self._cross_index_physiology(
            archetypes,
            physiological_events,
        )

        return (
            symbols, content, emotion, intensity, themes, archetypes,
            physiological_correlations, coding,
        )

    def _find_symbols(
        self,
        text: str,
        locale: str,
        coder: Optional[HvdcCoder] = None,
        clauses: Optional[List[Clause]] = None,
    ) -> List[DreamSymbol]:
        """
        Find and interpret symbols in dream text with contextual validation.

        A symbol counts only when it is PRESENT IN THE SCENE (v3): matches
        inside a negation («во сне не было воды», «без денег») are dropped,
        and a setting mentioned only to be rejected («копать в деревьях, а я
        решил копать не там») does not count either.
        """
        found_symbols = []
        text_lower = morphology.normalize(text)
        if coder is None:
            coder = get_hvdc_coder()
        if clauses is None:
            clauses = coder.segment(text)

        # Позиции стемовых совпадений считаем по токенам клауз — так у
        # каждого попадания есть клауза и индекс токена для проверки отрицания.
        for symbol_id, symbol_data in self.symbol_patterns.items():
            hits = [
                (m.start(), m.group(0))
                for m in symbol_data["pattern"].finditer(text_lower)
            ]
            if not hits:
                # Morphology pass: inflected Russian forms («воду»,
                # «змею», «матери») match by shared Snowball stem.
                for clause in clauses:
                    for tok in clause.tokens:
                        if morphology.stem(tok.text) in symbol_data["stems"]:
                            hits.append((tok.start, tok.text))

            valid = [
                (pos, surface) for pos, surface in hits
                if self._present_in_scene(symbol_id, symbol_data, pos, coder, clauses)
            ]
            if valid:
                # Contextual validation (v2.1 feature)
                surfaces = [surface for _, surface in valid]
                if self._validate_symbol_context(symbol_id, text_lower, surfaces):
                    data = symbol_data["data"]
                    found_symbols.append(DreamSymbol(
                        symbol=symbol_id,
                        category=DreamCategory(data["category"]),
                        frequency=len(valid),
                        significance=data["significance"],
                        interpretation_ru=data["interpretation_ru"],
                        interpretation_en=data["interpretation_en"],
                        archetype=data.get("archetype"),
                    ))

        # Sort by significance
        found_symbols.sort(key=lambda s: s.significance, reverse=True)
        return found_symbols

    def _present_in_scene(
        self,
        symbol_id: str,
        symbol_data: Dict,
        char_pos: int,
        coder: HvdcCoder,
        clauses: List[Clause],
    ) -> bool:
        """Negation and rejected-location filters for a single match."""
        clause = coder.clause_at(clauses, char_pos)
        if clause is None:
            return True
        tok_idx = coder.token_index_at(clause, char_pos)

        # «без денег», «нет воды», «не было лестницы» — прилегающее отрицание
        # или отрицание с бытийным глаголом в окне перед существительным.
        window = clause.tokens[max(0, tok_idx - 3):tok_idx]
        if window:
            if window[-1].text in coder._negators:
                return False
            has_negator = any(t.text in coder._negators for t in window)
            has_existential = any(t.text in _EXISTENTIAL_VERBS for t in window)
            if has_negator and has_existential:
                return False

        # Локация, упомянутая лишь как отвергнутая альтернатива.
        category = symbol_data["data"].get("category")
        if category == "settings" and coder.location_rejected_after(clauses, clause.index):
            return False
        return True

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
                # "throw X out (the) window" — not a house symbol, it's an
                # escape/disposal action. Common in surveillance dreams.
                (r'(throw|threw|выбро\w*|выкин\w*|кину\w*).{0,30}(window|окн)', ["window", "окно", "окна"]),
                (r'(throw|threw|выбро\w*|выкин\w*|кину\w*).{0,30}(door|дверь)', ["door", "дверь"]),
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
                    # (prefix check so inflected forms «дверью» match «дверь»)
                    for match in matches:
                        if any(match.lower().startswith(k.lower()) for k in excluded_keywords):
                            return False  # Found in exclusion context

        # Context reinforcement rules (boost confidence for good contexts)
        # Using word roots for Russian to match inflections
        reinforcement_contexts = {
            "surveillance": [
                # Strong indicators that surveillance is real theme.
                # Cover both following-root (след-/следи-) and tracking-root
                # (слеж-/слежения), which are spelled differently in Russian.
                r'(track|monitor|watch|follow|spy|след|слеж|наблюд|контрол|шпион)',
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

        # For symbols with reinforcement patterns, check for supporting context.
        # Most are SOFT (just trust the keyword match) — surveillance is STRICT
        # because lone keywords like "camera" produce too many false positives
        # ("I found a camera on the shelf" should NOT be surveillance).
        strict_reinforcement = {"surveillance"}

        if symbol_id in reinforcement_contexts:
            has_reinforcement = False
            for pattern_str in reinforcement_contexts[symbol_id]:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                if pattern.search(text):
                    has_reinforcement = True
                    break

            if symbol_id in strict_reinforcement:
                return has_reinforcement
            # Soft filter: trust the keyword match; the LLM does final
            # contextual validation downstream.
            return True

        # Default: symbol is valid (conservative approach)
        return True

    def _analyze_content(
        self,
        text: str,
        coding: HvdcCoding,
        coder: HvdcCoder,
        clauses: List[Clause],
    ) -> ContentAnalysis:
        """Hall/Van de Castle content analysis from the structural coding.

        Characters are distinct nouns (a pronoun is not a character), an
        interaction is an act WITH a target, misfortune/good fortune are
        their own categories rather than aliases of failure/success, and a
        ratio with an empty denominator is None — undefined, not zero."""

        male_chars = coding.count_characters("male")
        female_chars = coding.count_characters("female")
        animal_chars = coding.count_characters("animal")

        friendly = coding.count_events("friendliness")
        aggressive = coding.count_events("aggression")
        sexual = coding.count_events("sexuality")

        successes = coding.count_events("success")
        failures = coding.count_events("failure")
        misfortunes = coding.count_events("misfortune")
        good_fortunes = coding.count_events("good_fortune")

        positive_count = self._count_emotion_words(
            self.emotion_patterns["positive"], coder, clauses
        )
        negative_count = self._count_emotion_words(
            self.emotion_patterns["negative"], coder, clauses
        )

        # Ratios: undefined stays None. A zero numerator over a positive
        # denominator is a real 0.0; a zero denominator is not a number.
        male_female_ratio = male_chars / female_chars if female_chars > 0 else None
        agg_friend_ratio = aggressive / friendly if friendly > 0 else None
        success_fail_ratio = successes / failures if failures > 0 else None

        return ContentAnalysis(
            male_characters=male_chars,
            female_characters=female_chars,
            animal_characters=animal_chars,
            friendly_interactions=friendly,
            aggressive_interactions=aggressive,
            sexual_interactions=sexual,
            successes=successes,
            failures=failures,
            misfortunes=misfortunes,
            good_fortunes=good_fortunes,
            positive_emotions=positive_count,
            negative_emotions=negative_count,
            male_female_ratio=male_female_ratio,
            aggression_friendliness_ratio=agg_friend_ratio,
            success_failure_ratio=success_fail_ratio,
        )

    def _count_emotion_words(
        self,
        words: List[str],
        coder: HvdcCoder,
        clauses: List[Clause],
    ) -> int:
        """Count emotion-word occurrences outside negation («не боялся»
        is not fear). Russian entries match as prefixes to cover case and
        tense endings; English entries match as whole words."""
        count = 0
        norm_words = [morphology.normalize(w) for w in words]
        for clause in clauses:
            for tok in clause.tokens:
                if any(tok.text.startswith(w) for w in norm_words):
                    if not coder.is_negated(clause, tok.index):
                        count += 1
        return count

    def _analyze_emotions(
        self,
        text: str,
        coder: HvdcCoder,
        clauses: List[Clause],
    ) -> Tuple[EmotionType, float]:
        """Determine primary emotion and intensity using the knowledge
        base, skipping negated mentions («не боялся» is not fear)."""
        emotion_types = self.knowledge_base.get("emotions", {}).get("by_type", {})

        type_map = {
            "happiness": EmotionType.HAPPINESS,
            "sadness": EmotionType.SADNESS,
            "anger": EmotionType.ANGER,
            "fear": EmotionType.APPREHENSION,
            "confusion": EmotionType.CONFUSION,
        }
        emotion_counts = {e: 0 for e in type_map.values()}
        for key, emotion in type_map.items():
            emotion_counts[emotion] = self._count_emotion_words(
                emotion_types.get(key, []), coder, clauses
            )

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
