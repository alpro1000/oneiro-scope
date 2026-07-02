"""Light Russian morphology for symbol matching.

The dream knowledge base stores keywords as dictionary forms ("змея",
"вода", "мать"), but real dream texts arrive inflected («змею», «воду»,
«матери») — exact/prefix matching misses most Russian case endings, so
symbols silently drop out of the analysis. Live testing showed a typical
Russian dream losing 5 of 8 symbols to this.

This module implements the Snowball (Porter) stemmer for Russian in pure
Python — no dependencies — so the analyzer can compare *stems* of text
tokens against *stems* of keywords: «змею» → «зме» == stem(«змея»).
Suppletive verb forms the stemmer cannot unify («лечу»/«летать») are
covered by extra word forms in symbols.json.

Reference: M.F. Porter, "Russian stemming algorithm", snowballstem.org.
"""

from __future__ import annotations

import re

_VOWELS = "аеиоуыэюя"

_PERFECTIVE_GERUND_1 = ("вшись", "вши", "в")           # after а/я
_PERFECTIVE_GERUND_2 = ("ившись", "ывшись", "ивши", "ывши", "ив", "ыв")
_REFLEXIVE = ("ся", "сь")
_ADJECTIVE = (
    "ими", "ыми", "его", "ого", "ему", "ому", "ее", "ие", "ые", "ое",
    "ей", "ий", "ый", "ой", "ем", "им", "ым", "ом", "их", "ых",
    "ую", "юю", "ая", "яя", "ою", "ею",
)
_PARTICIPLE_1 = ("ем", "нн", "вш", "ющ", "щ")          # after а/я
_PARTICIPLE_2 = ("ивш", "ывш", "ующ")
_VERB_1 = (                                             # after а/я
    "ешь", "нно", "ете", "йте", "ла", "на", "ли", "ем", "ло", "но",
    "ет", "ют", "ны", "ть", "й", "л", "н",
)
_VERB_2 = (
    "ейте", "уйте", "ила", "ыла", "ена", "ите", "или", "ыли", "ило",
    "ыло", "ено", "ует", "уют", "ены", "ить", "ыть", "ишь", "ует",
    "ей", "уй", "ил", "ыл", "им", "ым", "ен", "ят", "ит", "ыт", "ую", "ю",
)
_NOUN = (
    "иями", "ями", "ами", "иях", "иям", "ием", "ией", "ии", "ие", "ье",
    "еи", "ей", "ой", "ий", "ям", "ем", "ам", "ом", "ах", "ях", "ию",
    "ью", "ия", "ья", "ев", "ов", "а", "е", "и", "й", "о", "у", "ы",
    "ь", "ю", "я",
)
_SUPERLATIVE = ("ейше", "ейш")
_DERIVATIONAL = ("ость", "ост")

_TOKEN_RE = re.compile(r"[а-яё]+", re.IGNORECASE)


def normalize(word: str) -> str:
    """Lowercase and fold ё→е (texts use both spellings)."""
    return word.lower().replace("ё", "е")


def _rv(word: str) -> int:
    """Start index of RV: the region after the first vowel."""
    for i, ch in enumerate(word):
        if ch in _VOWELS:
            return i + 1
    return len(word)


def _r2(word: str) -> int:
    """Start of R2: after the first non-vowel following a vowel, twice."""
    def _r(start: int) -> int:
        seen_vowel = False
        for i in range(start, len(word)):
            if word[i] in _VOWELS:
                seen_vowel = True
            elif seen_vowel:
                return i + 1
        return len(word)

    return _r(_r(0))


def _strip(word: str, rv: int, endings: tuple, after: str = "") -> str | None:
    """Remove the longest matching ending inside RV. With `after`, the
    ending must be preceded by one of those letters (which stays)."""
    for e in endings:
        if word.endswith(e) and len(word) - len(e) >= rv:
            if after:
                idx = len(word) - len(e) - 1
                if idx < 0 or word[idx] not in after:
                    continue
            return word[: len(word) - len(e)]
    return None


def stem(word: str) -> str:
    """Snowball Russian stem of a single word."""
    w = normalize(word)
    rv = _rv(w)

    # Step 1: perfective gerund, else (reflexive) + adj/participle/verb/noun.
    s = _strip(w, rv, _PERFECTIVE_GERUND_2) or _strip(
        w, rv, _PERFECTIVE_GERUND_1, after="ая"
    )
    if s is None:
        r = _strip(w, rv, _REFLEXIVE)
        if r is not None:
            w = r
        s = _strip(w, rv, _ADJECTIVE)
        if s is not None:
            w = s
            p = _strip(w, rv, _PARTICIPLE_2) or _strip(
                w, rv, _PARTICIPLE_1, after="ая"
            )
            if p is not None:
                w = p
        else:
            v = _strip(w, rv, _VERB_2) or _strip(w, rv, _VERB_1, after="ая")
            if v is not None:
                w = v
            else:
                n = _strip(w, rv, _NOUN)
                if n is not None:
                    w = n
    else:
        w = s

    # Step 2: trailing "и".
    if w.endswith("и") and len(w) - 1 >= rv:
        w = w[:-1]

    # Step 3: derivational ending in R2.
    r2 = _r2(normalize(word))
    d = _strip(w, r2, _DERIVATIONAL)
    if d is not None:
        w = d

    # Step 4: superlative, double н, trailing ь.
    s4 = _strip(w, rv, _SUPERLATIVE)
    if s4 is not None:
        w = s4
    if w.endswith("нн") and len(w) - 1 >= rv:
        w = w[:-1]
    if w.endswith("ь") and len(w) - 1 >= rv:
        w = w[:-1]
    return w


def keyword_stems(keywords: list[str], *, min_len: int = 3) -> set[str]:
    """Stems of the Cyrillic keywords, skipping stems too short to be
    safe (a 2-letter stem matches half the dictionary)."""
    out: set[str] = set()
    for kw in keywords:
        if re.search(r"[а-яё]", kw, re.IGNORECASE):
            st = stem(kw)
            if len(st) >= min_len:
                out.add(st)
    return out


def text_stems(text: str, *, min_len: int = 3) -> dict[str, int]:
    """Stem → count for every Cyrillic token in the text."""
    counts: dict[str, int] = {}
    for tok in _TOKEN_RE.findall(normalize(text)):
        st = stem(tok)
        if len(st) >= min_len:
            counts[st] = counts.get(st, 0) + 1
    return counts
