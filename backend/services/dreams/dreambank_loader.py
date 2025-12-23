"""
DreamBank Data Loader and Norm Comparator

Provides access to Hall/Van de Castle normative data for dream content analysis.
Based on research from DreamBank.net and the Hall & Van de Castle (1966) study.

References:
- Hall, C.S. & Van de Castle, R.L. (1966). The Content Analysis of Dreams.
- Domhoff, G.W. & Schneider, A. (2008). Studying dream content using DreamBank.net.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Gender(str, Enum):
    """Gender for norm comparison"""
    MALE = "male"
    FEMALE = "female"


@dataclass
class NormDeviation:
    """Represents deviation from Hall/Van de Castle norms"""
    indicator: str
    user_value: float
    norm_value: float
    deviation: float  # Percentage points difference
    deviation_percent: float  # Relative percentage difference
    significance: str  # "significant", "moderate", "normal"
    description_ru: str
    description_en: str


@dataclass
class NormComparison:
    """Complete norm comparison result"""
    gender_used: Gender
    deviations: List[NormDeviation]
    overall_typicality: float  # 0-100, how typical the dream is
    notable_findings_ru: List[str]
    notable_findings_en: List[str]


class DreamBankLoader:
    """
    Loads and manages Hall/Van de Castle normative data.

    Provides methods to compare dream content analysis results
    against established norms from the original 1966 study.
    """

    def __init__(self):
        self.norms: Dict = {}
        self.indicators: Dict = {}
        self.thresholds: Dict = {}
        self._load_norms()

    def _load_norms(self):
        """Load normative data from JSON file"""
        norms_path = Path(__file__).parent / "knowledge_base" / "hvdc_norms.json"
        try:
            with open(norms_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.norms = data.get("norms", {})
                self.indicators = data.get("indicators", {})
                self.thresholds = data.get("interpretation_thresholds", {
                    "significant_deviation": 15,
                    "moderate_deviation": 10
                })
                logger.info(f"Loaded HVDC norms: {len(self.indicators)} indicators")
        except FileNotFoundError:
            logger.warning("HVDC norms file not found, using defaults")
            self._set_default_norms()
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing HVDC norms: {e}")
            self._set_default_norms()

    def _set_default_norms(self):
        """Set hardcoded default norms if file not available"""
        self.norms = {
            "male": {
                "characters": {"male_percent": 67, "female_percent": 33},
                "social_interactions": {"aggression_friendliness_ratio": 0.59},
                "emotions": {"negative_percent": 80},
                "success_failure": {"success_percent": 51}
            },
            "female": {
                "characters": {"male_percent": 48, "female_percent": 52},
                "social_interactions": {"aggression_friendliness_ratio": 0.32},
                "emotions": {"negative_percent": 80},
                "success_failure": {"success_percent": 42}
            }
        }
        self.thresholds = {"significant_deviation": 15, "moderate_deviation": 10}

    def get_norm(self, gender: Gender, category: str, indicator: str) -> Optional[float]:
        """Get specific norm value for gender/category/indicator"""
        gender_norms = self.norms.get(gender.value, {})
        category_norms = gender_norms.get(category, {})
        return category_norms.get(indicator)

    def compare_to_norms(
        self,
        content_analysis: Dict,
        gender: Optional[str] = None
    ) -> NormComparison:
        """
        Compare dream content analysis to Hall/Van de Castle norms.

        Args:
            content_analysis: Dict with keys like male_characters, female_characters,
                            friendly_interactions, aggressive_interactions, etc.
            gender: Dreamer's gender for norm selection. If None, uses average.

        Returns:
            NormComparison with deviations and findings
        """
        # Determine which norms to use
        if gender and gender.lower() in ["male", "female"]:
            gender_used = Gender(gender.lower())
        else:
            gender_used = Gender.MALE  # Default, but could average

        deviations = []
        notable_findings_ru = []
        notable_findings_en = []

        # Calculate derived values from content analysis
        total_human = content_analysis.get("male_characters", 0) + content_analysis.get("female_characters", 0)
        male_percent = (content_analysis.get("male_characters", 0) / total_human * 100) if total_human > 0 else 50

        friendly = content_analysis.get("friendly_interactions", 0)
        aggressive = content_analysis.get("aggressive_interactions", 0)
        af_ratio = (aggressive / friendly) if friendly > 0 else (float(aggressive) if aggressive > 0 else 0)

        positive_emotions = content_analysis.get("positive_emotions", 0)
        negative_emotions = content_analysis.get("negative_emotions", 0)
        total_emotions = positive_emotions + negative_emotions
        negative_percent = (negative_emotions / total_emotions * 100) if total_emotions > 0 else 50

        successes = content_analysis.get("successes", 0)
        failures = content_analysis.get("failures", 0)
        total_outcomes = successes + failures
        success_percent = (successes / total_outcomes * 100) if total_outcomes > 0 else 50

        # Compare male/female character ratio
        norm_male_percent = self.norms.get(gender_used.value, {}).get("characters", {}).get("male_percent", 50)
        dev = self._calculate_deviation(
            user_value=male_percent,
            norm_value=norm_male_percent,
            indicator="male_female_percent",
            descriptions={
                "ru": "Процент мужских персонажей",
                "en": "Male character percentage"
            }
        )
        deviations.append(dev)
        if dev.significance != "normal":
            if male_percent > norm_male_percent:
                notable_findings_ru.append(f"Повышенное присутствие мужских персонажей ({male_percent:.0f}% vs норма {norm_male_percent}%)")
                notable_findings_en.append(f"Higher male character presence ({male_percent:.0f}% vs norm {norm_male_percent}%)")
            else:
                notable_findings_ru.append(f"Пониженное присутствие мужских персонажей ({male_percent:.0f}% vs норма {norm_male_percent}%)")
                notable_findings_en.append(f"Lower male character presence ({male_percent:.0f}% vs norm {norm_male_percent}%)")

        # Compare aggression/friendliness ratio
        norm_af_ratio = self.norms.get(gender_used.value, {}).get("social_interactions", {}).get("aggression_friendliness_ratio", 0.5)
        dev = self._calculate_deviation(
            user_value=af_ratio,
            norm_value=norm_af_ratio,
            indicator="aggression_friendliness_index",
            descriptions={
                "ru": "Индекс агрессия/дружелюбие",
                "en": "Aggression/Friendliness index"
            },
            is_ratio=True
        )
        deviations.append(dev)
        if dev.significance != "normal":
            if af_ratio > norm_af_ratio:
                notable_findings_ru.append(f"Повышенный уровень агрессии в социальных взаимодействиях (A/F={af_ratio:.2f} vs норма {norm_af_ratio:.2f})")
                notable_findings_en.append(f"Higher aggression in social interactions (A/F={af_ratio:.2f} vs norm {norm_af_ratio:.2f})")
            else:
                notable_findings_ru.append(f"Пониженный уровень агрессии, больше дружелюбия (A/F={af_ratio:.2f} vs норма {norm_af_ratio:.2f})")
                notable_findings_en.append(f"Lower aggression, more friendliness (A/F={af_ratio:.2f} vs norm {norm_af_ratio:.2f})")

        # Compare negative emotions percentage
        norm_negative = self.norms.get(gender_used.value, {}).get("emotions", {}).get("negative_percent", 80)
        dev = self._calculate_deviation(
            user_value=negative_percent,
            norm_value=norm_negative,
            indicator="negative_emotions_percent",
            descriptions={
                "ru": "Процент негативных эмоций",
                "en": "Negative emotions percentage"
            }
        )
        deviations.append(dev)
        if dev.significance != "normal":
            if negative_percent > norm_negative:
                notable_findings_ru.append(f"Выше среднего количество негативных эмоций ({negative_percent:.0f}%)")
                notable_findings_en.append(f"Higher than average negative emotions ({negative_percent:.0f}%)")
            else:
                notable_findings_ru.append(f"Ниже среднего количество негативных эмоций, более позитивный сон ({negative_percent:.0f}%)")
                notable_findings_en.append(f"Lower than average negative emotions, more positive dream ({negative_percent:.0f}%)")

        # Compare success/failure ratio
        norm_success = self.norms.get(gender_used.value, {}).get("success_failure", {}).get("success_percent", 50)
        dev = self._calculate_deviation(
            user_value=success_percent,
            norm_value=norm_success,
            indicator="dreamer_success_percent",
            descriptions={
                "ru": "Процент успехов сновидца",
                "en": "Dreamer success percentage"
            }
        )
        deviations.append(dev)
        if dev.significance != "normal":
            if success_percent > norm_success:
                notable_findings_ru.append(f"Повышенный процент успехов в сновидении ({success_percent:.0f}% vs норма {norm_success}%)")
                notable_findings_en.append(f"Higher success rate in dream ({success_percent:.0f}% vs norm {norm_success}%)")
            else:
                notable_findings_ru.append(f"Пониженный процент успехов, больше неудач ({success_percent:.0f}% vs норма {norm_success}%)")
                notable_findings_en.append(f"Lower success rate, more failures ({success_percent:.0f}% vs norm {norm_success}%)")

        # Calculate overall typicality score
        total_deviation = sum(abs(d.deviation) for d in deviations)
        avg_deviation = total_deviation / len(deviations) if deviations else 0
        # Convert to 0-100 scale where 100 is perfectly typical
        overall_typicality = max(0, min(100, 100 - avg_deviation * 2))

        return NormComparison(
            gender_used=gender_used,
            deviations=deviations,
            overall_typicality=overall_typicality,
            notable_findings_ru=notable_findings_ru,
            notable_findings_en=notable_findings_en
        )

    def _calculate_deviation(
        self,
        user_value: float,
        norm_value: float,
        indicator: str,
        descriptions: Dict[str, str],
        is_ratio: bool = False
    ) -> NormDeviation:
        """Calculate deviation from norm with significance assessment"""
        if is_ratio:
            # For ratios, calculate relative difference
            if norm_value > 0:
                deviation_percent = ((user_value - norm_value) / norm_value) * 100
            else:
                deviation_percent = 0 if user_value == 0 else 100
            deviation = deviation_percent / 5  # Normalize
        else:
            # For percentages, calculate absolute difference
            deviation = user_value - norm_value
            deviation_percent = (deviation / norm_value * 100) if norm_value > 0 else 0

        # Determine significance
        abs_deviation = abs(deviation)
        if abs_deviation >= self.thresholds.get("significant_deviation", 15):
            significance = "significant"
        elif abs_deviation >= self.thresholds.get("moderate_deviation", 10):
            significance = "moderate"
        else:
            significance = "normal"

        return NormDeviation(
            indicator=indicator,
            user_value=user_value,
            norm_value=norm_value,
            deviation=deviation,
            deviation_percent=deviation_percent,
            significance=significance,
            description_ru=descriptions.get("ru", indicator),
            description_en=descriptions.get("en", indicator)
        )

    def get_interpretation_context(
        self,
        comparison: NormComparison,
        locale: str = "ru"
    ) -> str:
        """
        Generate interpretation context based on norm comparison.

        This text can be added to the LLM prompt for more accurate interpretations.
        """
        if locale == "ru":
            lines = [
                f"Сравнение с нормами Hall/Van de Castle (пол: {comparison.gender_used.value}):",
                f"Типичность сна: {comparison.overall_typicality:.0f}%",
            ]
            if comparison.notable_findings_ru:
                lines.append("Отклонения от норм:")
                for finding in comparison.notable_findings_ru:
                    lines.append(f"• {finding}")
        else:
            lines = [
                f"Hall/Van de Castle norm comparison (gender: {comparison.gender_used.value}):",
                f"Dream typicality: {comparison.overall_typicality:.0f}%",
            ]
            if comparison.notable_findings_en:
                lines.append("Deviations from norms:")
                for finding in comparison.notable_findings_en:
                    lines.append(f"• {finding}")

        return "\n".join(lines)


# Singleton instance
_dreambank_loader: Optional[DreamBankLoader] = None


def get_dreambank_loader() -> DreamBankLoader:
    """Get singleton DreamBank loader instance"""
    global _dreambank_loader
    if _dreambank_loader is None:
        _dreambank_loader = DreamBankLoader()
    return _dreambank_loader
