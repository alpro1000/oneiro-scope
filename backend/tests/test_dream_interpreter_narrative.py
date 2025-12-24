"""
Dream Interpreter v2.1 - Narrative-First Semantic Engine Tests

Tests for contextual symbol validation and narrative-first analysis.
"""

import pytest
from backend.services.dreams.analyzer import DreamAnalyzer


class TestContextualSymbolValidation:
    """Test contextual validation of dream symbols (v2.1)."""

    def setup_method(self):
        """Initialize analyzer for each test."""
        self.analyzer = DreamAnalyzer()

    def test_excludes_house_symbol_from_car_door(self):
        """Should NOT detect 'house' symbol when 'door' appears in 'car door' context."""
        dream_text = "Я открыл дверь машины и сел в арендованный автомобиль."

        symbols, *_ = self.analyzer.analyze(dream_text, locale="ru")
        symbol_ids = [s.symbol for s in symbols]

        # Should detect 'vehicle' but NOT 'house'
        assert "vehicle" in symbol_ids, "Should detect vehicle symbol"
        assert "house" not in symbol_ids, "Should NOT detect house from 'car door'"

    def test_excludes_house_symbol_from_car_window(self):
        """Should NOT detect 'house' when 'window' appears in 'car window' context."""
        dream_text = "I looked through the car window and saw the city."

        symbols, *_ = self.analyzer.analyze(dream_text, locale="en")
        symbol_ids = [s.symbol for s in symbols]

        assert "house" not in symbol_ids, "Should NOT detect house from 'car window'"

    def test_includes_house_symbol_from_actual_house_door(self):
        """Should detect 'house' when door refers to actual house door."""
        dream_text = "Я подошёл к двери дома и открыл её ключом."

        symbols, *_ = self.analyzer.analyze(dream_text, locale="ru")
        symbol_ids = [s.symbol for s in symbols]

        assert "house" in symbol_ids, "Should detect house symbol from actual house door"

    def test_detects_surveillance_with_reinforcement(self):
        """Should detect 'surveillance' when tracking/monitoring context present."""
        dream_text = "Я взял монеты после аренды машины и понял, что арендодатель следит за мной через GPS-трекер."

        symbols, *_ = self.analyzer.analyze(dream_text, locale="ru")
        symbol_ids = [s.symbol for s in symbols]

        # Should detect surveillance-related symbols
        assert "surveillance" in symbol_ids, "Should detect surveillance from tracking context"
        assert "vehicle" in symbol_ids, "Should detect vehicle symbol"

    def test_excludes_surveillance_without_context(self):
        """Should NOT detect surveillance if keyword appears without monitoring context."""
        dream_text = "I found a camera on the shelf in my room."

        symbols, *_ = self.analyzer.analyze(dream_text, locale="en")
        symbol_ids = [s.symbol for s in symbols]

        # 'camera' keyword without surveillance context → should NOT trigger
        assert "surveillance" not in symbol_ids, "Should NOT detect surveillance without monitoring context"

    def test_detects_escape_liberation_with_throw_away(self):
        """Should detect 'escape_liberation' when throwing away/rejecting present."""
        dream_text = "Я выбросил монеты слежения в окно и почувствовал свободу."

        symbols, *_ = self.analyzer.analyze(dream_text, locale="ru")
        symbol_ids = [s.symbol for s in symbols]

        assert "escape_liberation" in symbol_ids, "Should detect liberation from 'throw away' action"

    def test_detects_control_with_manipulation_context(self):
        """Should detect 'control' when manipulation/domination context present."""
        dream_text = "Someone was manipulating me and controlling my decisions."

        symbols, *_ = self.analyzer.analyze(dream_text, locale="en")
        symbol_ids = [s.symbol for s in symbols]

        assert "control" in symbol_ids, "Should detect control from manipulation context"

    def test_car_tracking_dream_full_analysis(self):
        """
        Full integration test: car tracking dream should detect correct symbols.

        This is the original problem case from user feedback.
        """
        dream_text = """
        Я арендовал машину для поездки. После того как вернул её, арендодатель
        дал мне монеты обратно. Я понял, что в монетах встроены GPS-трекеры
        для слежения за мной. Я выбросил эти монеты в окно и почувствовал облегчение.
        """

        symbols, *_ = self.analyzer.analyze(dream_text, locale="ru")
        symbol_ids = [s.symbol for s in symbols]

        # SHOULD detect (contextually relevant)
        assert "vehicle" in symbol_ids, "Should detect vehicle (car rental)"
        assert "surveillance" in symbol_ids, "Should detect surveillance (GPS tracking)"
        assert "escape_liberation" in symbol_ids, "Should detect liberation (throwing away coins)"

        # Should NOT detect (false positives from old version)
        assert "house" not in symbol_ids, "Should NOT detect house (no house in dream)"
        assert "food" not in symbol_ids, "Should NOT detect food (no food in dream)"

    def test_excludes_food_from_food_truck(self):
        """Should NOT detect 'food' when focus is on truck, not food."""
        dream_text = "I saw a food truck driving down the street."

        symbols, *_ = self.analyzer.analyze(dream_text, locale="en")
        symbol_ids = [s.symbol for s in symbols]

        # Focus is on vehicle/truck, not food
        assert "food" not in symbol_ids, "Should NOT detect food from 'food truck' when truck is focus"

    def test_boundaries_with_violation_context(self):
        """Should detect 'boundaries' when violation/invasion context present."""
        dream_text = "Кто-то вторгся в моё личное пространство и нарушил границы."

        symbols, *_ = self.analyzer.analyze(dream_text, locale="ru")
        symbol_ids = [s.symbol for s in symbols]

        assert "boundaries" in symbol_ids, "Should detect boundaries from violation context"

    def test_multiple_symbols_sorted_by_significance(self):
        """Symbols should be sorted by significance score."""
        dream_text = "I was falling from the sky while flying over water during a storm."

        symbols, *_ = self.analyzer.analyze(dream_text, locale="en")

        # Verify symbols are sorted (first should have highest significance)
        if len(symbols) > 1:
            for i in range(len(symbols) - 1):
                assert symbols[i].significance >= symbols[i + 1].significance, \
                    "Symbols should be sorted by significance (descending)"


class TestNarrativeFirstAnalysis:
    """Test narrative-first semantic analysis approach."""

    def setup_method(self):
        """Initialize analyzer for each test."""
        self.analyzer = DreamAnalyzer()

    def test_modern_symbols_loaded(self):
        """Should load all modern symbols (surveillance, control, etc.)."""
        modern_symbols = [
            "surveillance",
            "boundaries",
            "control",
            "escape_liberation",
            "privacy",
            "autonomy",
            "technology_device",
        ]

        for symbol_id in modern_symbols:
            assert symbol_id in self.analyzer.symbol_patterns, \
                f"Modern symbol '{symbol_id}' should be loaded"

    def test_total_symbol_count(self):
        """Should have 56 total symbols (50 original + 7 modern - 1 jewel original)."""
        total_symbols = len(self.analyzer.symbol_patterns)

        # Should have at least 56 symbols (original 50 + 7 new modern)
        assert total_symbols >= 56, \
            f"Should have at least 56 symbols, got {total_symbols}"

    def test_symbol_has_required_fields(self):
        """Each symbol should have required fields for interpretation."""
        for symbol_id, symbol_data in self.analyzer.symbol_patterns.items():
            data = symbol_data["data"]

            assert "interpretation_ru" in data, f"Symbol {symbol_id} missing interpretation_ru"
            assert "interpretation_en" in data, f"Symbol {symbol_id} missing interpretation_en"
            assert "significance" in data, f"Symbol {symbol_id} missing significance"
            assert "category" in data, f"Symbol {symbol_id} missing category"
            assert "keywords" in data, f"Symbol {symbol_id} missing keywords"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
