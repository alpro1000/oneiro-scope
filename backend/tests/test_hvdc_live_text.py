"""WP-4/WP-5: live-text HVdC regressions + statistical honesty thresholds.

The July audit ran the coder on the owner's real dream and got male=0 and
GF=0 while the test suite was green — every failing construction here is
quoted from that audit, not authored by the agent («Ни один приёмочный
критерий не формулируется на тексте, написанном самим агентом»).
"""

import pytest

from backend.services.dreams.dreambank_loader import DreamBankLoader
from backend.services.dreams.hvdc_coder import HvdcCoder


@pytest.fixture(scope="module")
def coder():
    return HvdcCoder()


# ---------------------------------------------------------------------------
# WP-4 §1: substantivized adjectives are characters with morphological gender
# ---------------------------------------------------------------------------

def test_audit_fragment_senior_acquaintance_is_one_male(coder):
    # Verbatim fragment from the owner's dream (July audit, run 2).
    coding = coder.code(
        "Мне снится, что старший знакомый, с которым я иногда советуюсь, "
        "говорит, где нужно копать."
    )
    males = [c for c in coding.characters if c.gender == "male"]
    assert len(males) == 1, f"male expected 1, got {coding.characters}"
    assert males[0].noun == "знакомый"


@pytest.mark.parametrize("text,noun", [
    ("Ко мне подошёл прохожий и что-то спросил.", "прохожий"),
    ("Дежурный записал моё имя в журнал.", "дежурный"),
])
def test_substantivized_adjectives_are_male_characters(coder, text, noun):
    coding = coder.code(text)
    assert [(c.noun, c.gender) for c in coding.characters] == [(noun, "male")]


def test_feminine_form_gets_female_gender(coder):
    coding = coder.code("Ко мне подошла знакомая и улыбнулась.")
    assert [(c.noun, c.gender) for c in coding.characters] == [("знакомая", "female")]


def test_plural_substantivized_is_indefinite(coder):
    coding = coder.code("Вокруг стояли знакомые и молчали.")
    assert [(c.noun, c.gender) for c in coding.characters] == [("знакомые", "indefinite")]


def test_adjective_before_noun_is_attribute_not_second_character(coder):
    # «старший брат» is one male, not «старший» + «брат».
    coding = coder.code("Старший брат обнял меня.")
    assert [(c.noun, c.gender) for c in coding.characters] == [("брат", "male")]


# ---------------------------------------------------------------------------
# WP-4 §2: good fortune from valuables without a find-verb
# ---------------------------------------------------------------------------

def _gf(coding):
    return [e for e in coding.events if e.category == "good_fortune"]


def test_audit_fragment_coins_lying_under_bush_is_gf(coder):
    # The audit's live run coded this construction GF=0.
    coding = coder.code(
        "Я копаю землю у старого дома и вижу: под кустом лежат золотые монеты."
    )
    assert len(_gf(coding)) == 1
    assert _gf(coding)[0].subtype == "discovery"


def test_turns_out_treasure_is_one_gf_not_two(coder):
    # Enumeration «клад, старинные золотые монеты» is one windfall.
    coding = coder.code(
        "Открываю шкатулку — там оказывается клад, старинные золотые монеты."
    )
    assert len(_gf(coding)) == 1


def test_english_gold_coins_lying_is_gf(coder):
    coding = coder.code("I dig near the old house and see gold coins lying under a bush.")
    assert len(_gf(coding)) == 1


def test_find_verb_plus_valuables_still_one_gf(coder):
    coding = coder.code("Я нашёл клад: золотые монеты лежат в сундуке.")
    assert len(_gf(coding)) == 1


@pytest.mark.parametrize("text", [
    "Там не было золота, только пыль.",          # genitive-of-negation
    "Не вижу никаких монет вокруг.",              # negated perception
    "Мы гуляли по старому кладбищу вечером.",     # кладбище ≠ клад
    "Каменная кладка стены обрушилась.",          # кладка ≠ клад
])
def test_valuable_discovery_guards(coder, text):
    assert _gf(coder.code(text)) == []


@pytest.mark.skip(
    reason="Ожидает полный дословный текст «монетного сна» от владельца "
    "(передаётся вместе со слепой разметкой WP-17); проверенные фрагменты "
    "из аудита покрыты тестами выше."
)
def test_full_verbatim_coin_dream_expected_coding(coder):
    pass


# ---------------------------------------------------------------------------
# WP-5: indicators below the event threshold are insufficient, not values
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def loader():
    return DreamBankLoader()


def _base(**overrides):
    content = {
        "male_characters": 0, "female_characters": 0,
        "friendly_interactions": 0, "aggressive_interactions": 0,
        "positive_emotions": 0, "negative_emotions": 0,
        "successes": 0, "failures": 0,
    }
    content.update(overrides)
    return content


def test_af_from_one_plus_one_is_insufficient(loader):
    """The audit's exact case: 1 aggression + 1 friendliness produced a
    confident A/F=1.00 against the norm. Two events are an anecdote."""
    cmp = loader.compare_to_norms(
        _base(friendly_interactions=1, aggressive_interactions=1), gender="male"
    )
    assert all(d.indicator != "aggression_friendliness_index" for d in cmp.deviations)
    thin = [i for i in cmp.insufficient_data
            if i.indicator == "aggression_friendliness_index"]
    assert thin and thin[0].events_observed == 2
    assert thin[0].min_events_required == 3


def test_af_from_three_events_is_compared_with_counts(loader):
    cmp = loader.compare_to_norms(
        _base(friendly_interactions=2, aggressive_interactions=1), gender="male"
    )
    dev = next(d for d in cmp.deviations
               if d.indicator == "aggression_friendliness_index")
    assert dev.events_observed == 3
    assert dev.min_events_required == 3


def test_single_character_is_insufficient_for_gender_split(loader):
    cmp = loader.compare_to_norms(_base(male_characters=1), gender="male")
    thin = [i for i in cmp.insufficient_data if i.indicator == "male_female_percent"]
    assert thin and thin[0].events_observed == 1 and thin[0].min_events_required == 2


def test_zero_zero_still_reported_as_indeterminate(loader):
    cmp = loader.compare_to_norms(_base(), gender="male")
    af = [i for i in cmp.insufficient_data
          if i.indicator == "aggression_friendliness_index"]
    assert af and af[0].events_observed == 0


def test_typicality_warning_on_thin_basis(loader):
    cmp = loader.compare_to_norms(
        _base(male_characters=2, female_characters=1), gender="male"
    )
    # One admitted indicator over 3 events — a hint, not a measurement.
    assert cmp.typicality_warning_ru and cmp.typicality_warning_en


def test_typicality_warning_when_nothing_compared(loader):
    cmp = loader.compare_to_norms(_base(), gender="male")
    assert not cmp.deviations
    assert "не рассчитывалась" in cmp.typicality_warning_ru
    # An uncomputed score must not masquerade as a perfect 100 (Qodo #7).
    assert cmp.overall_typicality is None
