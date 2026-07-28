"""Structural Hall/Van de Castle coder.

The previous encoder counted keyword hits over the whole dream text, which
is not how HVdC works: the system codes *events between characters* —
who did what to whom, and what befell whom. A bag of words cannot see that
"отдал фигурки женщине" is a friendliness act (giving, F-scale) or that
"оттеснил наблюдателя" is physical aggression without harm (A-scale), and
it counted "не нашёл" the same as "нашёл".

This module extracts structure deterministically — no LLM:

1. The text is segmented into sentences and clauses.
2. Characters are found per clause (noun lexicon + RU agent-suffix
   heuristics), deduplicated by stem: a dream mentioning «женщина …
   женщине» has ONE female character, and pronouns never create
   characters (the old counter turned every «он/его» into a male).
3. Acts are matched per clause from `knowledge_base/hvdc_lexicon.json`
   (exact surface forms + bounded prefix roots). Social interactions
   (aggression / friendliness / sexuality) require a target character or
   personal pronoun in the same clause or the previous clause of the
   sentence — a lone verb is not an interaction.
4. Negation is scoped: a negator right before the act kills it, and for
   striving verbs recodes it («не смог» → failure, not zero events).
   Discovery verbs preceded by effort markers recode good fortune into
   success («долго искал и наконец нашёл»), following the HVdC rule that
   good fortune is a benefit arriving WITHOUT effort or another
   character's intent.

Every coded event carries its evidence clause and a source citation, so
the confidence-1.0 claim is auditable item by item.

Reference: Hall & Van de Castle (1966), *The Content Analysis of Dreams*;
Domhoff (1996), *Finding Meaning in Dreams* (coding rules).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.services.dreams import morphology

HVDC_CODER_VERSION = "3.1.0"

_LEXICON_PATH = Path(__file__).parent / "knowledge_base" / "hvdc_lexicon.json"

_TOKEN_RE = re.compile(r"[a-zа-яё]+(?:['’\-][a-zа-яё]+)*", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"[.!?;\n]+")

# Максимум букв окончания после корневого префикса: «толкн»+«ули» — да,
# «напа»+«дение» — нет (иначе существительные липнут к глагольным корням).
_MAX_ROOT_TAIL = 4
# Отрицание действует на глагол в окне трёх токенов слева: «так и не нашёл».
_NEGATION_WINDOW = 3

_SOURCE = {
    "aggression": "Hall & Van de Castle (1966), aggression scale (A1–A8)",
    "friendliness": "Hall & Van de Castle (1966), friendliness scale (F1–F7)",
    "sexuality": "Hall & Van de Castle (1966), sexuality scale (S1–S5)",
    "good_fortune": "Hall & Van de Castle (1966), good fortune (GF)",
    "misfortune": "Hall & Van de Castle (1966), misfortune (M1–M6)",
    "success": "Hall & Van de Castle (1966), success (SU)",
    "failure": "Hall & Van de Castle (1966), failure (FL)",
}


@dataclass
class Token:
    text: str          # normalized surface form
    start: int         # char offset in the normalized full text
    index: int         # position within the clause


@dataclass
class Clause:
    text: str
    start: int         # char offset of the clause in the normalized text
    end: int
    sentence_index: int
    index: int         # global clause index
    tokens: List[Token] = field(default_factory=list)


@dataclass
class CharacterMention:
    noun: str
    gender: str        # male | female | indefinite | animal
    clause_index: int


@dataclass
class CodedEvent:
    category: str      # aggression|friendliness|sexuality|good_fortune|misfortune|success|failure
    subtype: str
    actor: str
    target: Optional[str]
    evidence: str      # the clause the event was read from
    source: str        # citation of the coding rule


@dataclass
class HvdcCoding:
    clauses: List[Clause]
    characters: List[CharacterMention]
    events: List[CodedEvent]
    coder_version: str = HVDC_CODER_VERSION

    def count_characters(self, gender: str) -> int:
        return sum(1 for c in self.characters if c.gender == gender)

    def count_events(self, category: str) -> int:
        return sum(1 for e in self.events if e.category == category)


class HvdcCoder:
    """Deterministic clause-level HVdC extractor over the shared lexicon."""

    def __init__(self, lexicon_path: Optional[Path] = None):
        with open(lexicon_path or _LEXICON_PATH, encoding="utf-8") as f:
            lex = json.load(f)
        self._lex = lex

        self._negators = {
            morphology.normalize(w)
            for words in lex["negators"].values()
            for w in words
        }
        self._splitters = {
            morphology.normalize(w)
            for words in lex["clause_splitters"].values()
            for w in words
        }
        self._contrast = {
            morphology.normalize(w)
            for words in lex["contrast_markers"].values()
            for w in words
        }
        self._location_rejection = [
            morphology.normalize(p)
            for phrases in lex["location_rejection"].values()
            for p in phrases
        ]
        self._target_pronouns = {
            morphology.normalize(w)
            for words in lex["target_pronouns"].values()
            for w in words
        }

        # Character lexicon. Russian tokens resolve through the pymorphy3
        # LEMMA (жены/жене/женой → жена; отца → отец; пса → пёс; детьми →
        # ребёнок), so the lexicon lists dictionary forms only. English
        # tokens match exact forms. The old stem map misgendered whole
        # classes: stem(«жених») == stem(«жена») == «жен».
        self._char_forms: Dict[str, str] = {}
        self._char_phrases: List[Tuple[str, str]] = []
        for gender in ("female", "male", "indefinite", "animal"):
            by_lang = lex["characters"].get(gender, {})
            for words in by_lang.values():
                for w in words:
                    norm = morphology.normalize(w)
                    if " " in norm:
                        self._char_phrases.append((norm, gender))
                    else:
                        key = (
                            morphology.lemma_info(norm).normal_form
                            if _is_cyrillic(norm)
                            else norm
                        )
                        self._char_forms.setdefault(key, gender)
                        # Surface form as written stays a valid key too
                        # («матери» lemma is «мать», both must resolve).
                        self._char_forms.setdefault(norm, gender)

        # Агентивные суффиксы применяются к ЛЕММЕ и только к одушевлённым
        # существительным (animacy-гейт pymorphy3): «наблюдатель» → male,
        # «учительница» → female; «граница», «постель», «чайник» отсечены
        # неодушевлённостью, «лисица» — не-агентивным суффиксом.
        self._male_agent_tails = ("тель", "щик", "чик", "ник")
        self._female_agent_tails = ("тельница", "льница", "щица", "чица")

        # WP-4: субстантивированные прилагательные («знакомый», «старший»,
        # «прохожий», «дежурный»). У многих в OpenCorpora вообще нет
        # NOUN-разбора, поэтому членство — курируемый список лемм, а род
        # даёт морфология конкретной ФОРМЫ (знакомая → female).
        self._subst_lemmas = frozenset(
            morphology.normalize(w)
            for w in lex.get("substantivized_adjectives", {}).get("ru", ())
        )

        # WP-4: находка ценностей без глагола «нашёл» — good fortune.
        vd = lex.get("valuable_discovery", {})
        self._presence_forms = {
            morphology.normalize(w)
            for key in ("presence_ru_forms", "presence_en_forms")
            for w in vd.get(key, ())
        }
        self._presence_phrases = [
            morphology.normalize(p) for p in vd.get("presence_en_phrases", ())
        ]
        self._valuables_ru_roots = [
            morphology.normalize(w) for w in vd.get("valuables_ru_roots", ())
        ]
        self._valuables_ru_excl = tuple(
            morphology.normalize(w) for w in vd.get("valuables_ru_exclusions", ())
        )
        self._valuables_en = {
            morphology.normalize(w) for w in vd.get("valuables_en", ())
        }

        # Acts: exact forms, prefix roots, and multiword substring patterns.
        self._acts = []
        for act in lex["acts"]:
            forms = set()
            roots: List[str] = []
            phrases: List[str] = []
            for key in ("ru_forms", "en_forms"):
                for w in act.get(key, ()):  # exact token equality
                    norm = morphology.normalize(w)
                    if " " in norm:
                        phrases.append(norm)
                    else:
                        forms.add(norm)
            for key in ("ru_roots", "en_roots"):
                for w in act.get(key, ()):
                    norm = morphology.normalize(w)
                    if " " in norm:
                        phrases.append(norm)
                    else:
                        roots.append(norm)
            self._acts.append(
                {
                    "category": act["category"],
                    "subtype": act["subtype"],
                    "requires_target": act.get("requires_target", False),
                    "effort_recodes_to_success": act.get(
                        "effort_recodes_to_success", False
                    ),
                    "negation_recodes_to_failure": act.get(
                        "negation_recodes_to_failure", False
                    ),
                    "forms": forms,
                    "roots": roots,
                    "phrases": phrases,
                }
            )

        self._effort_markers = {
            morphology.normalize(w)
            for words in lex["effort_markers"].values()
            for w in words
        }
        # «пытался решить, но провалил» / "tried to solve but failed" —
        # глагол успеха после маркера попытки называет цель, а не достижение.
        self._attempt_markers = {
            morphology.normalize(w)
            for words in lex.get("attempt_markers", {}).values()
            for w in words
        }
        self._effort_phrases = [m for m in self._effort_markers if " " in m]
        self._chance_context = [
            morphology.normalize(w)
            for words in lex["chance_win_context"].values()
            for w in words
        ]
        self._win_roots = [
            morphology.normalize(w) for w in lex["win_forms"].get("ru_roots", ())
        ]
        self._win_forms = {
            morphology.normalize(w) for w in lex["win_forms"].get("en_forms", ())
        }

    # ------------------------------------------------------------------
    # Segmentation
    # ------------------------------------------------------------------

    def segment(self, text: str) -> List[Clause]:
        """Sentences on [.!?;], clauses on commas and clause-level
        conjunctions (а, но, когда, but, then, …). Offsets refer to the
        normalized text so symbol matching can share the clause map."""
        norm = morphology.normalize(text)
        clauses: List[Clause] = []
        sent_start = 0
        sentence_index = 0

        boundaries = [m.end() for m in _SENTENCE_SPLIT_RE.finditer(norm)]
        if not boundaries or boundaries[-1] < len(norm):
            boundaries.append(len(norm))

        for sent_end in boundaries:
            sentence = norm[sent_start:sent_end]
            if sentence.strip():
                for c_start, c_end in self._split_clauses(sentence):
                    abs_start = sent_start + c_start
                    abs_end = sent_start + c_end
                    chunk = norm[abs_start:abs_end]
                    if not chunk.strip():
                        continue
                    clause = Clause(
                        text=chunk,
                        start=abs_start,
                        end=abs_end,
                        sentence_index=sentence_index,
                        index=len(clauses),
                    )
                    clause.tokens = [
                        Token(text=m.group(0), start=abs_start + m.start(), index=i)
                        for i, m in enumerate(_TOKEN_RE.finditer(chunk))
                    ]
                    clauses.append(clause)
                sentence_index += 1
            sent_start = sent_end

        return clauses

    def _split_clauses(self, sentence: str) -> List[Tuple[int, int]]:
        cut_points = [0]
        for m in re.finditer(r"[,:]", sentence):
            cut_points.append(m.end())
        for m in _TOKEN_RE.finditer(sentence):
            if m.group(0) in self._splitters and m.start() > 0:
                cut_points.append(m.start())
        cut_points = sorted(set(cut_points))
        spans = []
        for i, start in enumerate(cut_points):
            end = cut_points[i + 1] if i + 1 < len(cut_points) else len(sentence)
            if end > start:
                spans.append((start, end))
        return spans

    # ------------------------------------------------------------------
    # Negation
    # ------------------------------------------------------------------

    def is_negated(self, clause: Clause, token_index: int) -> bool:
        """A negator within the window right before the token negates it:
        «так и не нашёл», "did not find". Window, not whole clause — in
        «я нашёл не то, что искал» the finding itself stands."""
        lo = max(0, token_index - _NEGATION_WINDOW)
        return any(
            t.text in self._negators for t in clause.tokens[lo:token_index]
        )

    def clause_negates_presence(self, clause: Clause, token_index: int) -> bool:
        """Existential negation kills nouns: «там не было воды», "there was
        no water", «без денег». Any negator before the noun in the clause.

        Russian also negates existence with the noun FIRST — родительный
        отрицания: «водителя не было», «воды нет». Caught by negator +
        existential right after a genitive-marked noun (the genitive is
        what separates it from «мама не была рада», where the nominative
        subject is present, just not glad)."""
        if any(t.text in self._negators for t in clause.tokens[:token_index]):
            return True
        noun = clause.tokens[token_index] if token_index < len(clause.tokens) else None
        if noun is not None and _is_cyrillic(noun.text):
            info = morphology.lemma_info(noun.text)
            if info.case in ("gent", "gen2"):
                after = clause.tokens[token_index + 1 : token_index + 4]
                has_negator = any(t.text in self._negators for t in after)
                has_existential = any(
                    t.text in ("было", "был", "была", "нет", "видно", "оказалось")
                    for t in after
                )
                if has_negator and has_existential:
                    return True
        return False

    def location_rejected_after(self, clauses: List[Clause], clause_index: int) -> bool:
        """«…копать в деревьях, а я решил копать не там» — the setting is
        mentioned only to be rejected in the NEXT clause: a contrast marker
        plus an anaphoric location negation («не там», "not there")."""
        current = clauses[clause_index]
        for cl in clauses[clause_index + 1 : clause_index + 3]:
            has_contrast = any(t.text in self._contrast for t in cl.tokens) or (
                cl.sentence_index == current.sentence_index
            )
            if has_contrast and any(p in cl.text for p in self._location_rejection):
                return True
        return False

    # ------------------------------------------------------------------
    # Characters
    # ------------------------------------------------------------------

    def _character_gender(self, token: str) -> Optional[str]:
        exact = self._char_forms.get(token)
        if exact in ("male", "female", "animal"):
            return exact
        if _is_cyrillic(token):
            info = morphology.lemma_info(token)
            lemma_gender = self._char_forms.get(info.normal_form)
            if lemma_gender in ("male", "female", "animal"):
                return lemma_gender
            # WP-4: субстантивированные прилагательные — род из морфологии
            # формы, не из словарного indefinite: «знакомый» → male,
            # «знакомая» → female, «знакомых» (мн.) → indefinite.
            subst = morphology.form_gender_for_lemmas(token, self._subst_lemmas)
            if subst is not None:
                return subst
            if exact or lemma_gender:
                return exact or lemma_gender  # словарный indefinite
            # Агентивные суффиксы по лемме, только для одушевлённых
            # существительных: «водителя» → водитель → male.
            if info.pos == "NOUN" and info.animate and len(info.normal_form) >= 6:
                if info.normal_form.endswith(self._female_agent_tails):
                    return "female"
                if info.normal_form.endswith(self._male_agent_tails):
                    return "male"
            return None
        # "ex-girlfriend" carries the same character as "girlfriend".
        if token.startswith("ex-"):
            return self._char_forms.get(token[3:])
        return exact

    def _character_key(self, token: str) -> str:
        """Dedup key: lemma for Russian («отца … отец» — один персонаж),
        the token itself for English."""
        if _is_cyrillic(token):
            return morphology.lemma_info(token).normal_form
        return token[3:] if token.startswith("ex-") else token

    def _is_attribute_before_character(self, clause: Clause, tok: Token) -> bool:
        """«Старший знакомый» — «старший» здесь прилагательное при персонаже,
        а не второй персонаж. Кандидат из субстантивированного класса
        пропускается, когда сразу за ним стоит другой персонаж-токен."""
        if not _is_cyrillic(tok.text):
            return False
        if morphology.form_gender_for_lemmas(tok.text, self._subst_lemmas) is None:
            return False
        nxt = tok.index + 1
        if nxt >= len(clause.tokens):
            return False
        return self._character_gender(clause.tokens[nxt].text) is not None

    def find_characters(self, clauses: List[Clause]) -> List[CharacterMention]:
        mentions: List[CharacterMention] = []
        seen_keys: set = set()
        for clause in clauses:
            for tok in clause.tokens:
                gender = self._character_gender(tok.text)
                if gender is None:
                    continue
                if self._is_attribute_before_character(clause, tok):
                    continue  # «старший знакомый» — один персонаж, не два
                if self.clause_negates_presence(clause, tok.index):
                    continue  # «никого не было», «без людей»
                key = self._character_key(tok.text)
                if key in seen_keys:
                    continue  # одно существительное = один персонаж
                seen_keys.add(key)
                mentions.append(
                    CharacterMention(
                        noun=tok.text, gender=gender, clause_index=clause.index
                    )
                )
            for phrase, gender in self._char_phrases:
                if phrase in clause.text and phrase not in seen_keys:
                    # «old man» — если «man» уже посчитан токеном, фраза
                    # описывает того же персонажа, не второго.
                    last_key = self._character_key(phrase.split()[-1])
                    if last_key in seen_keys:
                        continue
                    seen_keys.add(phrase)
                    seen_keys.add(last_key)
                    mentions.append(
                        CharacterMention(
                            noun=phrase, gender=gender, clause_index=clause.index
                        )
                    )
        return mentions

    # ------------------------------------------------------------------
    # Acts
    # ------------------------------------------------------------------

    def _match_act(self, token: str) -> Optional[dict]:
        for act in self._acts:
            if token in act["forms"]:
                return act
            for root in act["roots"]:
                if (
                    token.startswith(root)
                    and len(token) - len(root) <= _MAX_ROOT_TAIL
                ):
                    return act
        return None

    def _has_target(
        self, clauses: List[Clause], clause: Clause, characters_by_clause: Dict[int, List[CharacterMention]]
    ) -> Optional[str]:
        """Target = a character or personal pronoun in this clause, or in
        the previous clause of the same sentence (anaphora window).
        Character detection is token-level, NOT the deduplicated mention
        list — «ударил змею» has a target even though the snake was first
        introduced two sentences earlier."""
        found = self._target_in_clause(clause)
        if found:
            return found
        prev_idx = clause.index - 1
        if prev_idx >= 0:
            prev = clauses[prev_idx]
            if prev.sentence_index == clause.sentence_index:
                return self._target_in_clause(prev)
        return None

    def _target_in_clause(self, clause: Clause) -> Optional[str]:
        for tok in clause.tokens:
            if self._character_gender(tok.text) is not None:
                if not self.clause_negates_presence(clause, tok.index):
                    return tok.text
        for tok in clause.tokens:
            if tok.text in self._target_pronouns:
                return tok.text
        return None

    def _effort_nearby(self, clauses: List[Clause], clause: Clause) -> bool:
        """Effort markers in the same sentence recode a discovery from good
        fortune into success («долго искал и наконец нашёл»). Same sentence
        only — a "finally" one sentence back usually closes a different
        episode, not this finding."""
        for cl in clauses:
            if cl.sentence_index == clause.sentence_index:
                if any(t.text in self._effort_markers for t in cl.tokens):
                    return True
                if any(p in cl.text for p in self._effort_phrases):
                    return True
        return False

    def _actor_for(self, clause: Clause, characters_by_clause, act_token: Token) -> str:
        """First-person dream narration defaults the actor to the dreamer
        unless a character noun precedes the verb in the same clause."""
        own = characters_by_clause.get(clause.index, [])
        for mention in own:
            for tok in clause.tokens:
                if tok.text == mention.noun and tok.index < act_token.index:
                    return mention.noun
        return "dreamer"

    def code(self, text: str, clauses: Optional[List[Clause]] = None) -> HvdcCoding:
        if clauses is None:
            clauses = self.segment(text)
        characters = self.find_characters(clauses)
        characters_by_clause: Dict[int, List[CharacterMention]] = {}
        for c in characters:
            characters_by_clause.setdefault(c.clause_index, []).append(c)

        events: List[CodedEvent] = []
        gf_valuable_sentences: set = set()

        for clause in clauses:
            # HVdC кодирует событие, а не глагол: «споткнулся и упал» — одно
            # несчастье, «схватил и ударил» — одна физическая агрессия.
            # Дубликаты (категория, подтип) внутри клаузы схлопываются.
            seen_in_clause: set = set()

            def add(category: str, subtype: str, actor: str, target: Optional[str], *, _clause=None):
                cl = _clause or clause
                if (category, subtype) in seen_in_clause:
                    return
                seen_in_clause.add((category, subtype))
                events.append(
                    CodedEvent(
                        category=category,
                        subtype=subtype,
                        actor=actor,
                        target=target,
                        evidence=cl.text.strip(),
                        source=_SOURCE[category],
                    )
                )

            for tok in clause.tokens:
                act = self._match_act(tok.text)
                win = self._match_win(tok.text)
                if act is None and win is None:
                    continue
                negated = self.is_negated(clause, tok.index)

                if win is not None and act is None:
                    if negated:
                        continue
                    if any(w in clause.text for w in self._chance_context):
                        add("good_fortune", "luck", "dreamer", None)
                    else:
                        add("success", "achievement", "dreamer", None)
                    continue

                category = act["category"]
                if negated:
                    if act.get("negation_recodes_to_failure") or category == "good_fortune":
                        # «не смог», «не нашёл» — striving unfulfilled.
                        add("failure", "failure", "dreamer", None)
                    continue

                if category == "success" and self._attempt_before(clause, tok.index):
                    continue  # «пытался решить…» — цель, не достижение

                if category == "good_fortune" and act.get("effort_recodes_to_success"):
                    if self._discovery_is_not_fortune(clause, tok.index):
                        # "I found myself in a room", "found that…",
                        # «наконец нашёл его.» — состояние, эпистемика или
                        # нахождение человека, не приобретение ценности.
                        # Калибровка на norms-корпусе: ×3.9 перебора GF шло
                        # в основном из этих трёх идиом.
                        continue
                    if self._effort_nearby(clauses, clause):
                        add("success", "achievement", "dreamer", None)
                        continue

                if act["requires_target"]:
                    target = self._has_target(clauses, clause, characters_by_clause)
                    if target is None:
                        continue  # interaction needs someone on the other end
                    actor = self._actor_for(clause, characters_by_clause, tok)
                    add(category, act["subtype"], actor, target)
                else:
                    add(category, act["subtype"], "dreamer", None)

            for act in self._acts:
                for phrase in act["phrases"]:
                    pos = clause.text.find(phrase)
                    if pos == -1:
                        continue
                    # Фразовый путь обязан соблюдать те же инварианты, что
                    # токенный: «он НЕ пожал мне руку» — не дружелюбие
                    # (ревью Qodo на PR #166 поймало обход отрицания).
                    phrase_tok = self.token_index_at(clause, clause.start + pos)
                    if self.is_negated(clause, phrase_tok):
                        continue
                    if act["requires_target"]:
                        target = self._has_target(clauses, clause, characters_by_clause)
                        if target is None:
                            continue
                        if phrase_tok < len(clause.tokens):
                            actor = self._actor_for(
                                clause, characters_by_clause, clause.tokens[phrase_tok]
                            )
                        else:
                            actor = "dreamer"
                        add(act["category"], act["subtype"], actor, target)
                    else:
                        add(act["category"], act["subtype"], "dreamer", None)

            # WP-4: находка ценностей без глагола «нашёл» — «под кустом
            # лежат золотые монеты», «оказывается клад». Одно событие на
            # предложение: перечисление «клад, старинные монеты» — одна
            # удача, не две; «нашёл клад» (глагольный путь выше) тоже
            # закрывает предложение от повторного GF по ценности.
            if any(cat == "good_fortune" for cat, _ in seen_in_clause):
                gf_valuable_sentences.add(clause.sentence_index)
            self._code_valuable_discovery(clauses, clause, add, gf_valuable_sentences)

        return HvdcCoding(clauses=clauses, characters=characters, events=events)

    def _valuable_token(self, clause: Clause) -> Optional[Token]:
        for tok in clause.tokens:
            text = tok.text
            if text in self._valuables_en:
                return tok
            if _is_cyrillic(text):
                if any(text.startswith(x) for x in self._valuables_ru_excl):
                    continue  # «кладбище», «кладка» — не сокровища
                for root in self._valuables_ru_roots:
                    if text.startswith(root) and len(text) - len(root) <= 3:
                        return tok
        return None

    def _presence_token(self, clause: Clause) -> Optional[Token]:
        """Non-negated presence/perception verb in the clause, or None."""
        if not clause.tokens:
            return None
        for tok in clause.tokens:
            if tok.text in self._presence_forms:
                if not self.is_negated(clause, tok.index):
                    return tok
        for phrase in self._presence_phrases:
            pos = clause.text.find(phrase)
            if pos != -1:
                idx = self.token_index_at(clause, clause.start + pos)
                if not self.is_negated(clause, idx):
                    return clause.tokens[min(idx, len(clause.tokens) - 1)]
        return None

    def _code_valuable_discovery(
        self,
        clauses: List[Clause],
        clause: Clause,
        add,
        coded_sentences: set,
    ) -> None:
        """Good fortune из ценности + глагола наличия/восприятия (WP-4).

        Живой прогон аудита: «копаю землю … вижу: под кустом лежат золотые
        монеты» кодировался GF=0, потому что все правила GF висели на
        глаголах находки. Ценность («золото», «клад», «монеты»…) вместе с
        «лежат»/«вижу»/«оказывается» в том же предложении — приобретение
        по стечению обстоятельств, GF по Hall & Van de Castle. Отрицание
        любой из частей («не было золота», «не вижу монет») гасит событие.
        """
        if clause.sentence_index in coded_sentences:
            return
        valuable = self._valuable_token(clause)
        if valuable is None:
            return
        if self.clause_negates_presence(clause, valuable.index):
            return
        presence = self._presence_token(clause)
        if presence is None:
            # «вижу: под кустом монеты» — глагол в соседней клаузе того же
            # предложения.
            for other in clauses:
                if other.sentence_index == clause.sentence_index and other is not clause:
                    presence = self._presence_token(other)
                    if presence is not None:
                        break
        if presence is None:
            return
        coded_sentences.add(clause.sentence_index)
        add("good_fortune", "discovery", "dreamer", None, _clause=clause)

    def _attempt_before(self, clause: Clause, token_index: int) -> bool:
        return any(
            t.text in self._attempt_markers for t in clause.tokens[:token_index]
        )

    _REFLEXIVES = {
        "myself", "ourselves", "himself", "herself", "themselves", "itself",
        "yourself", "себя", "себе",
    }
    # «found that …» / «found out» / «нашёл, что» — эпистемика (узнал),
    # не приобретение ценности.
    _EPISTEMIC_AFTER = {"that", "out", "что"}
    # «наконец нашёл его.» (клауза кончается местоимением) — нахождение
    # ЧЕЛОВЕКА, социальный исход, не good fortune. Не срабатывает на
    # «нашёл его кошелёк» — там за местоимением идёт объект.
    _PERSON_OBJECT_PRONOUNS = {"him", "them", "me", "us", "его", "ее", "их", "меня", "нас"}

    def _reflexive_after(self, clause: Clause, token_index: int) -> bool:
        nxt = clause.tokens[token_index + 1 : token_index + 2]
        return bool(nxt) and nxt[0].text in self._REFLEXIVES

    def _discovery_is_not_fortune(self, clause: Clause, token_index: int) -> bool:
        nxt = clause.tokens[token_index + 1 : token_index + 2]
        if not nxt:
            return False
        if nxt[0].text in self._REFLEXIVES or nxt[0].text in self._EPISTEMIC_AFTER:
            return True
        is_last = nxt[0].index == len(clause.tokens) - 1
        return is_last and nxt[0].text in self._PERSON_OBJECT_PRONOUNS

    def _match_win(self, token: str) -> Optional[bool]:
        if token in self._win_forms:
            return True
        for root in self._win_roots:
            if token.startswith(root) and len(token) - len(root) <= _MAX_ROOT_TAIL:
                return True
        return None

    # ------------------------------------------------------------------
    # Helpers shared with the symbol/emotion side of the analyzer
    # ------------------------------------------------------------------

    def clause_at(self, clauses: List[Clause], char_pos: int) -> Optional[Clause]:
        for clause in clauses:
            if clause.start <= char_pos < clause.end:
                return clause
        return None

    def token_index_at(self, clause: Clause, char_pos: int) -> int:
        for tok in clause.tokens:
            if tok.start <= char_pos < tok.start + len(tok.text):
                return tok.index
        return len(clause.tokens)


def _is_cyrillic(word: str) -> bool:
    return bool(re.search(r"[а-яё]", word))


_coder: Optional[HvdcCoder] = None


def get_hvdc_coder() -> HvdcCoder:
    global _coder
    if _coder is None:
        _coder = HvdcCoder()
    return _coder
