"""Golden-set evaluation of the structural HVdC coder.

28 hand-coded dreams (16 RU + 12 EN) in tests/dreams/golden/ carry
expected Hall/Van de Castle counts coded by a human reading of the text —
not by what the engine outputs. The test prints per-category precision
and recall (micro-averaged over dreams) and fails CI when any category
drops below its floor.

SCOPE OF THE NUMBERS: annotations and coder share an author, so this
measures INTERNAL CONSISTENCY and guards against regressions — it is not
external accuracy. A shared misreading of the HVdC rules would pass here
unnoticed. External check: a second annotator codes the same texts blind
(golden/blind_annotation_template.json) and scripts/kappa_golden.py
reports weighted Cohen's kappa per category; disagreements get
adjudicated against the primary source and whichever side is wrong
(golds OR coder) gets fixed.

Floors are set from the measured 2026-07-27 baseline (P=1.00 everywhere;
R=0.70–1.00) with a small margin. Recall floors below 1.0 correspond to
DOCUMENTED gaps: modal inability («не мог кричать»), gesture verbs
(«махали», «аплодировали»), and pronoun-based character gender. Raising
recall must never be bought with precision — the coder is precision-first
by design.
"""

import json
from collections import defaultdict
from pathlib import Path

import pytest

from backend.services.dreams.analyzer import DreamAnalyzer
from backend.services.dreams.dreambank_loader import get_dreambank_loader

GOLDEN_DIR = Path(__file__).parent / "dreams" / "golden"

FIELDS = [
    "male_characters", "female_characters", "animal_characters",
    "friendly_interactions", "aggressive_interactions", "sexual_interactions",
    "successes", "failures", "misfortunes", "good_fortunes",
]

# CI floors. Precision is the product's promise (no invented events);
# recall floors mark the honest coverage of the current lexicon.
PRECISION_FLOOR = {f: 0.90 for f in FIELDS}
RECALL_FLOOR = {
    "male_characters": 0.85,
    "female_characters": 0.90,
    "animal_characters": 0.90,
    "friendly_interactions": 0.70,
    "aggressive_interactions": 0.90,
    "sexual_interactions": 0.90,
    "successes": 0.90,
    "failures": 0.60,
    "misfortunes": 0.90,
    "good_fortunes": 0.90,
}
SYMBOL_INCLUDE_RECALL_FLOOR = 0.90


def _load_dreams():
    dreams = []
    for name in ("golden_ru.json", "golden_en.json"):
        with open(GOLDEN_DIR / name, encoding="utf-8") as f:
            dreams += json.load(f)["dreams"]
    return dreams


@pytest.fixture(scope="module")
def analyzer():
    return DreamAnalyzer()


def test_golden_set_size():
    dreams = _load_dreams()
    assert 25 <= len(dreams) <= 40, "golden set must hold 25+ dreams"
    locales = {d["locale"] for d in dreams}
    assert locales == {"ru", "en"}


def test_golden_precision_recall(analyzer):
    dreams = _load_dreams()
    tp, fp, fn = defaultdict(int), defaultdict(int), defaultdict(int)
    sym_inc_total = sym_inc_hit = 0
    sym_violations = []

    for d in dreams:
        symbols, content, *_ = analyzer.analyze(d["text"], d["locale"])
        pred = content.model_dump()
        sym_ids = {s.symbol for s in symbols}
        for f in FIELDS:
            g, p = d["expected"][f], pred[f]
            tp[f] += min(g, p)
            fp[f] += max(0, p - g)
            fn[f] += max(0, g - p)
        for s in d["symbols_must_include"]:
            sym_inc_total += 1
            sym_inc_hit += s in sym_ids
        for s in d["symbols_must_exclude"]:
            if s in sym_ids:
                sym_violations.append((d["id"], s))

    print("\nHVdC golden metrics (micro-averaged over %d dreams)" % len(dreams))
    print(f"{'category':28} {'P':>6} {'R':>6}   tp/fp/fn")
    failures = []
    for f in FIELDS:
        P = tp[f] / (tp[f] + fp[f]) if tp[f] + fp[f] else 1.0
        R = tp[f] / (tp[f] + fn[f]) if tp[f] + fn[f] else 1.0
        print(f"{f:28} {P:6.2f} {R:6.2f}   {tp[f]}/{fp[f]}/{fn[f]}")
        if P < PRECISION_FLOOR[f]:
            failures.append(f"{f}: precision {P:.2f} < floor {PRECISION_FLOOR[f]}")
        if R < RECALL_FLOOR[f]:
            failures.append(f"{f}: recall {R:.2f} < floor {RECALL_FLOOR[f]}")

    sym_recall = sym_inc_hit / sym_inc_total if sym_inc_total else 1.0
    print(f"{'symbols_must_include':28} {'':6} {sym_recall:6.2f}   {sym_inc_hit}/{sym_inc_total}")
    print(f"symbol false positives: {sym_violations}")

    if sym_recall < SYMBOL_INCLUDE_RECALL_FLOOR:
        failures.append(f"symbol include recall {sym_recall:.2f} < {SYMBOL_INCLUDE_RECALL_FLOOR}")
    if sym_violations:
        failures.append(f"false symbols on golden set: {sym_violations}")

    assert not failures, "\n".join(failures)


def test_acceptance_coins_dream(analyzer):
    """Задание, критерий 1: сон про монеты кодируется с ненулевыми
    friendly/aggressive/good_fortunes."""
    dreams = {d["id"]: d for d in _load_dreams()}
    text = dreams["g01_coins"]["text"]
    _, content, *_ = analyzer.analyze(text, "ru")
    assert content.friendly_interactions >= 1
    assert content.aggressive_interactions >= 1
    assert content.good_fortunes >= 1


def test_zero_interactions_are_insufficient_not_zero():
    """Задание, критерий 2: 0 агрессии / 0 дружелюбия — неопределённость.
    Индикатор A/F исключается с пометкой, а не подаётся как 0.00."""
    loader = get_dreambank_loader()
    comparison = loader.compare_to_norms(
        {
            "male_characters": 0, "female_characters": 0,
            "friendly_interactions": 0, "aggressive_interactions": 0,
            "successes": 0, "failures": 0,
            "positive_emotions": 0, "negative_emotions": 0,
        },
        gender="male",
    )
    compared = {d.indicator for d in comparison.deviations}
    assert "aggression_friendliness_index" not in compared
    insufficient = {i.indicator for i in comparison.insufficient_data}
    assert "aggression_friendliness_index" in insufficient
    # ... и ни один индикатор не сравнивался: данных нет вообще.
    assert not comparison.deviations
    assert len(comparison.insufficient_data) == 4


def test_aggression_without_friendliness_is_undefined_ratio():
    loader = get_dreambank_loader()
    comparison = loader.compare_to_norms(
        {
            "male_characters": 1, "female_characters": 0,
            "friendly_interactions": 0, "aggressive_interactions": 2,
            "successes": 0, "failures": 0,
            "positive_emotions": 0, "negative_emotions": 1,
        },
        gender="male",
    )
    compared = {d.indicator for d in comparison.deviations}
    assert "aggression_friendliness_index" not in compared
    insufficient = {i.indicator for i in comparison.insufficient_data}
    assert "aggression_friendliness_index" in insufficient


def test_deviation_units_are_explicit():
    loader = get_dreambank_loader()
    comparison = loader.compare_to_norms(
        {
            "male_characters": 3, "female_characters": 1,
            "friendly_interactions": 1, "aggressive_interactions": 2,
            "successes": 1, "failures": 1,
            "positive_emotions": 1, "negative_emotions": 3,
        },
        gender="male",
    )
    units = {d.indicator: d.deviation_unit for d in comparison.deviations}
    assert units["male_female_percent"] == "percentage_points"
    assert units["aggression_friendliness_index"] == "ratio"
    af = next(d for d in comparison.deviations if d.indicator == "aggression_friendliness_index")
    # deviation живёт в родных единицах индикатора: 2/1 - 0.59 = 1.41
    assert af.deviation == pytest.approx(1.41, abs=0.01)


def test_negated_symbols_do_not_appear(analyzer):
    symbols, *_ = analyzer.analyze("Во сне не было воды и огня.", "ru")
    ids = {s.symbol for s in symbols}
    assert "water" not in ids
    assert "fire" not in ids


def test_genitive_of_negation_removes_character(analyzer):
    """«Водителя не было видно» — родительный отрицания: существительное
    стоит ПЕРЕД «не было», персонаж отсутствует. А «мама не была рада» —
    именительный: мама в сцене есть."""
    *_, coding_absent = analyzer.analyze("Водителя не было видно.", "ru")
    assert coding_absent.characters == []
    *_, coding_present = analyzer.analyze("Мама не была рада подарку.", "ru")
    assert [c.gender for c in coding_present.characters] == ["female"]


def test_negated_phrase_acts_code_nothing(analyzer):
    """Фразовые акты идут через тот же скоуп отрицания, что и токенные
    (ревью Qodo на PR #166): «не пожал руку» — не дружелюбие,
    «не занимались любовью» — не сексуальность."""
    *_, negated = analyzer.analyze("Старик не пожал мне руку.", "ru")
    assert negated.count_events("friendliness") == 0
    *_, positive = analyzer.analyze("Старик пожал мне руку.", "ru")
    assert positive.count_events("friendliness") == 1
    *_, negated_s = analyzer.analyze("Мы с невестой не занимались любовью.", "ru")
    assert negated_s.count_events("sexuality") == 0


def test_lemma_distinguishes_bride_groom_class(analyzer):
    """стем(«жених») == стем(«жена») — класс коллизий, закрытый
    pymorphy3-леммой, а не заплаткой на точную форму."""
    *_, with_wife = analyzer.analyze("Мы с женой прыгали от счастья.", "ru")
    assert [c.gender for c in with_wife.characters] == ["female"]
    *_, with_groom = analyzer.analyze("Жениха ждали у алтаря.", "ru")
    assert [c.gender for c in with_groom.characters] == ["male"]


def test_rejected_location_does_not_appear(analyzer):
    symbols, *_ = analyzer.analyze(
        "Мне сказали копать в деревьях, а я решил копать не там.", "ru"
    )
    ids = {s.symbol for s in symbols}
    assert "forest" not in ids


def test_negation_flips_success_to_failure(analyzer):
    _, content, *_ = analyzer.analyze("Я не смог открыть дверь.", "ru")
    assert content.failures == 1
    assert content.successes == 0


@pytest.mark.asyncio
async def test_lunar_context_filled_when_date_given():
    """Задание, критерий 6: lunar_context заполняется при переданной дате."""
    from backend.services.dreams.service import DreamService
    from backend.services.dreams.schemas import DreamAnalysisRequest
    from datetime import date

    svc = DreamService()
    resp = await svc.analyze_dream(
        DreamAnalysisRequest(
            dream_text="Мне снилось спокойное поле под луной.",
            dream_date=date(2026, 7, 20),
            locale="ru",
        ),
        interpret=False,
    )
    assert resp.lunar_context is not None
    assert 1 <= resp.lunar_context.lunar_day <= 30
    assert resp.lunar_context.lunar_phase


@pytest.mark.asyncio
async def test_mcp_analyze_dream_is_data_first():
    """Задание, критерии 5 и 7: серверная проза выключена по умолчанию на
    MCP-пути; disclaimer присутствует; мёртвые поля не отдаются."""
    from backend.mcp.tools.dreams import analyze_dream

    out = await analyze_dream(
        "Мне снилось, что я нашёл монеты и отдал их женщине.",
        dreamer_gender="male",
        locale="ru",
    )
    assert "interpretation" not in out
    assert "summary" not in out
    assert "recommendations" not in out
    assert "physiological_correlations" not in out
    assert out["how_to_read"]
    assert out["disclaimer"]
    # Провенанс пособытийно: каждый счётчик подтверждён клаузой.
    assert out["content_analysis"]["good_fortunes"] == len(
        [e for e in out["hvdc_evidence"] if e["category"] == "good_fortune"]
    )


def test_all_dreams_tools_carry_disclaimer():
    from backend.mcp.tools.dreams import (
        list_archetypes,
        list_dream_symbols,
        list_hvdc_categories,
    )

    for result in (list_dream_symbols(), list_archetypes(), list_hvdc_categories()):
        assert result["disclaimer"], f"missing disclaimer in {result}"
