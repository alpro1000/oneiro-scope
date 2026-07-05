"""Trait dimensions: weighted consensus of KB readings per behavioral
dimension — the system's OWN verdict, computed first time, instead of
printing contradictory clauses side by side and asking the user.

Live case that forced this layer (2026-07-05): «общительность» — three
clauses said sociable (dilated, water, pyknic), one weak clause said
not (thin lips «скупость на слова»). Presented raw, the portrait
flip-flopped; weighted, the system gets it right on the first pass.

Deterministic composition: every contribution cites the KB clause it
comes from; weights are fixed here, scaled by cross-frame support;
background (lens-sensitive) readings count at half weight. When the
net signal is weak or evidence conflicts, the verdict is honestly
`unclear` — WITH what is needed to make the trait readable.
"""

from __future__ import annotations

# topic → (signed weight, the KB clause fragment that justifies it)
# Dimension weights are relative plausibility of the clause for the
# dimension, NOT new knowledge: every entry quotes its dictionary.
_DIMENSIONS: list[tuple[str, dict, dict]] = [
    ("sociability", {"ru": "Общительность", "en": "Sociability"}, {
        "corman.dilated": (+1.0, "экстенсивный контакт со средой"),
        "five_elements.water": (+0.8, "коммуникабельность"),
        "kretschmer.pyknic": (+0.6, "общительность в своём кругу"),
        "features.mouth_full": (+0.4, "щедрость выражения"),
        "features.mouth_thin": (-0.4, "скупость на слова"),
    }),
    ("inner_privacy", {"ru": "Закрытость личной глубины",
                       "en": "Guarded inner depth"}, {
        "features.mouth_thin": (+0.8, "надёжность в тайне"),
        "five_elements.water": (+0.6, "скрытность глубин"),
        "features.eyelid_heavy": (+0.6, "закрытый внутренний контур"),
        "features.mouth_full": (-0.4, "щедрость выражения"),
    }),
    ("perseverance", {"ru": "Упорство, доведение до конца",
                      "en": "Perseverance"}, {
        "five_elements.earth": (+1.0, "выносливость и завершение начатого"),
        "kretschmer.athletic": (+0.8, "несбиваемость"),
        "features.jaw_wide": (+0.6, "воля к завершению, «дожимает»"),
        "five_elements.fire": (-0.4, "выгорание"),
    }),
    ("assertiveness", {"ru": "Напористость в конфликте",
                       "en": "Assertiveness"}, {
        "fwhr.high": (+0.8, "напористость в конкуренции"),
        "fwhr.low": (-0.8, "меньшая склонность к силовой конкуренции"),
        "five_elements.water": (-0.4, "обтекать препятствия"),
        "features.cheekbones_high": (+0.6, "умение держать позицию"),
    }),
    ("emotionality", {"ru": "Эмоциональная вовлечённость",
                      "en": "Emotional engagement"}, {
        "lavater_zones.middle": (+0.9, "эмоциональная жизнь и характер контакта"),
        "three_courts.middle": (+0.6, "воля, самореализация"),
        "features.eyes_large": (+0.6, "эмоциональная отзывчивость"),
        "features.mouth_full": (+0.3, "вкус к жизни"),
    }),
    ("practicality", {"ru": "Практичность, материальность",
                      "en": "Practicality"}, {
        "five_elements.earth": (+0.8, "практичность, накопление ресурса"),
        "three_courts.lower": (+0.8, "исполнение и материя, хозяйственность"),
        "lavater_zones.lower": (+0.5, "сила дела и аппетит к материальному"),
        "five_elements.wood": (-0.4, "идеализм"),
    }),
    ("expressiveness", {"ru": "Экспрессия и скорость",
                        "en": "Expressiveness and speed"}, {
        "five_elements.fire": (+1.0, "экспрессия, харизма, скорость"),
        "kretschmer.athletic": (-0.6, "медленный разгон"),
        "five_elements.water": (+0.2, "адаптивность"),
    }),
    ("stubbornness", {"ru": "Упрямство, инертность к переменам",
                      "en": "Stubbornness"}, {
        "five_elements.earth": (+0.8, "инертность и упрямство"),
        "five_elements.metal": (+0.4, "жёсткость к себе и другим"),
        "kretschmer.athletic": (+0.4, "долгая память на несправедливость"),
        "five_elements.water": (-0.3, "адаптивность"),
    }),
]

# Contributors geometry cannot see → how to make them visible.
_HOW_TO_SEE = {
    "features.eyelid_heavy": {"ru": "анкета: тяжёлое ли верхнее веко",
                              "en": "questionnaire: heavy upper eyelid?"},
    "features.eyes_large": {"ru": "анкета: крупные ли глаза",
                            "en": "questionnaire: large eyes?"},
    "features.cheekbones_high": {"ru": "анкета: выражены ли скулы",
                                 "en": "questionnaire: pronounced cheekbones?"},
    "features.mouth_thin": {"ru": "3+ кадра с закрытым ртом",
                            "en": "3+ closed-mouth frames"},
    "features.mouth_full": {"ru": "3+ кадра с закрытым ртом",
                            "en": "3+ closed-mouth frames"},
}

_QUESTIONNAIRE_ONLY = {"features.eyelid_heavy", "features.eyes_large",
                       "features.cheekbones_high"}

STRONG, LEAN, CONFLICT_MIN = 1.2, 0.5, 0.4

_VERDICT = {
    "ru": {"high": "выражена", "lean_high": "скорее да",
           "unclear": "не читается уверенно", "lean_low": "скорее нет",
           "low": "выражено слабо"},
    "en": {"high": "pronounced", "lean_high": "leaning yes",
           "unclear": "not readable with confidence",
           "lean_low": "leaning no", "low": "weakly expressed"},
}


def _support_share(reading: dict) -> float:
    sup = reading.get("support")
    if not sup:
        return 1.0
    n, m = sup.split("/")
    return int(n) / max(1, int(m))


def dimension_verdicts(readings: list[dict], locale: str = "ru",
                       mouth_frames: int = 0) -> list[dict]:
    """Weighted consensus per dimension over the aggregated readings.

    Each verdict lists its evidence (clause + signed contribution), so
    the synthesis stays auditable. Background readings count at half
    weight (lens sensitivity). `mouth_frames` — closed-mouth frames
    available; 0 means mouth-driven evidence is missing, not absent.
    """
    loc = "en" if locale == "en" else "ru"
    by_topic = {r["topic"]: r for r in readings}
    out = []
    for key, label, contribs in _DIMENSIONS:
        pos = neg = 0.0
        evidence, missing = [], []
        for topic, (weight, clause) in contribs.items():
            r = by_topic.get(topic)
            if r is None:
                if topic in _QUESTIONNAIRE_ONLY:
                    missing.append(_HOW_TO_SEE[topic][loc])
                elif topic.startswith("features.mouth_") and mouth_frames < 3:
                    how = _HOW_TO_SEE[topic][loc]
                    if how not in missing:
                        missing.append(how)
                continue
            share = _support_share(r)
            w = weight * share
            if r.get("scope") == "background":
                w *= 0.5
            evidence.append({"topic": topic, "clause": clause,
                             "contribution": round(w, 2),
                             "source": r["source"]})
            if w >= 0:
                pos += w
            else:
                neg += -w
        score = round(pos - neg, 2)
        conflicted = min(pos, neg) >= CONFLICT_MIN
        if abs(score) >= STRONG and not conflicted:
            verdict = "high" if score > 0 else "low"
        elif abs(score) >= LEAN:
            verdict = "lean_high" if score > 0 else "lean_low"
        else:
            verdict = "unclear"
        needed = list(missing)
        if verdict == "unclear":
            if conflicted:
                needed.append(
                    "признаки противоречат — нужны кадры с дистанции 2+ м "
                    "(задняя камера) и анкета" if loc == "ru" else
                    "signals conflict — need 2+ m distance shots (rear "
                    "camera) and the questionnaire")
            elif not evidence:
                needed.append(
                    "по фото не видно — нужна анкета или управляемый скан"
                    if loc == "ru" else
                    "not visible in photos — questionnaire or guided scan")
            else:
                needed.append(
                    "сигнал слабый — нужно больше фронтальных кадров "
                    "(разные дни, дистанция 2+ м) и анкета" if loc == "ru"
                    else "weak signal — more frontal frames (different "
                    "days, 2+ m distance) and the questionnaire")
        out.append({
            "dimension": key,
            "label": label[loc],
            "verdict": verdict,
            "verdict_label": _VERDICT[loc][verdict],
            "score": score,
            "conflicted": conflicted,
            "evidence": evidence,
            "needed": needed,
        })
    return out
