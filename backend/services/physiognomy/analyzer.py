"""Metrics/answers → traditional readings from the knowledge base.

Thresholds are documented heuristics over anthropometric ratios
(neutral averages: width/length ~0.72, jaw/cheek ~0.85, inner-canthal
distance ≈ one eye width). Interpretations come ONLY from the KB —
every reading carries its source; nothing is generated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from backend.services.physiognomy.schemas import (
    ElementScore,
    FaceMetrics,
    FeatureAnswers,
    Fullness,
    Reading,
    Size,
    Spacing,
)

_KB_DIR = Path(__file__).parent / "knowledge_base"


def _load(name: str) -> dict:
    with open(_KB_DIR / name, encoding="utf-8") as f:
        return json.load(f)


MIANXIANG = _load("mianxiang.json")
WESTERN = _load("western.json")


def _t(entry: dict, locale: str) -> str:
    return entry.get(locale) or entry.get("ru") or entry.get("en") or ""


def element_scores(m: FaceMetrics) -> list[ElementScore]:
    """Score the five elements from shape ratios.

    Each score is a sum of closeness terms in [0..1]; the shapes are
    fuzzy prototypes, so we rank rather than hard-classify.
    """
    wl, jc = m.width_length, m.jaw_cheek

    def near(x: float, target: float, tol: float) -> float:
        return max(0.0, 1.0 - abs(x - target) / tol)

    scores = {
        # Earth: wide AND strong-jawed.
        "earth": near(wl, 0.80, 0.12) + near(jc, 0.95, 0.15),
        # Water: wide but soft-jawed (round).
        "water": near(wl, 0.80, 0.12) + near(jc, 0.72, 0.12),
        # Wood: long and narrow.
        "wood": near(wl, 0.62, 0.10) + near(jc, 0.80, 0.20) * 0.5,
        # Fire: narrow pointed chin under an average-wide face.
        "fire": near(wl, 0.72, 0.10) * 0.5 + near(jc, 0.62, 0.12),
        # Metal: rectangular — moderate width, defined jaw.
        "metal": near(wl, 0.70, 0.08) + near(jc, 0.88, 0.10) * 0.8,
    }
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    return [ElementScore(element=e, score=round(s, 3)) for e, s in ranked]


def dominant_court(m: FaceMetrics) -> str:
    courts = {
        "upper": m.upper_court,
        "middle": m.middle_court,
        "lower": m.lower_court,
    }
    return max(courts, key=courts.get)


def readings_from_metrics(m: FaceMetrics, locale: str) -> list[Reading]:
    out: list[Reading] = []
    fe = MIANXIANG["five_elements"]

    ranked = element_scores(m)
    for rank, es in enumerate(ranked[:2]):
        entry = fe[es.element]
        prefix = "" if rank == 0 else ("вторичный оттенок — " if locale == "ru" else "secondary shade — ")
        out.append(Reading(
            system="mianxiang",
            topic=f"five_elements.{es.element}",
            text=prefix + _t(entry["reading"], locale),
            source=entry["source"],
        ))

    court = dominant_court(m)
    tc = MIANXIANG["three_courts"][court]
    out.append(Reading(
        system="mianxiang", topic=f"three_courts.{court}",
        text=_t(tc["reading"], locale), source=tc["source"],
    ))
    lz = WESTERN["lavater_zones"][court]
    out.append(Reading(
        system="lavater", topic=f"lavater_zones.{court}",
        text=_t(lz, locale), source=lz["source"],
    ))

    # Corman: frame width decides dilated/retracted.
    corman_key = "dilated" if m.width_length >= 0.74 else "retracted"
    cz = WESTERN["corman"][corman_key]
    out.append(Reading(
        system="corman", topic=f"corman.{corman_key}",
        text=_t(cz, locale), source=cz["source"],
    ))

    # Kretschmer approximation from the same frame ratios.
    if m.width_length >= 0.76:
        kk = "pyknic" if m.jaw_cheek < 0.9 else "athletic"
    elif m.width_length <= 0.66:
        kk = "asthenic"
    else:
        kk = "athletic" if m.jaw_cheek >= 0.9 else "pyknic"
    kz = WESTERN["kretschmer"][kk]
    out.append(Reading(
        system="kretschmer", topic=f"kretschmer.{kk}",
        text=_t(kz, locale), source=kz["source"],
    ))

    # fWHR — neutral ~1.9 in the literature; flag only clear deviations.
    if m.fwhr >= 2.0 or m.fwhr <= 1.7:
        fk = "high" if m.fwhr >= 2.0 else "low"
        fz = WESTERN["fwhr_note"][fk]
        out.append(Reading(
            system="fwhr", topic=f"fwhr.{fk}",
            text=_t(fz, locale), source=fz["source"],
        ))

    feats = MIANXIANG["features"]
    if m.eye_spacing >= 1.12:
        out.append(_feat(feats, "eyes_wide_set", locale))
    elif m.eye_spacing <= 0.88:
        out.append(_feat(feats, "eyes_close_set", locale))
    if m.jaw_cheek >= 0.95:
        out.append(_feat(feats, "jaw_wide", locale))
    if m.nose_width is not None and m.nose_width >= 0.28:
        out.append(_feat(feats, "nose_fleshy", locale))
    if m.lip_fullness is not None:
        if m.lip_fullness >= 0.065:
            out.append(_feat(feats, "mouth_full", locale))
        elif m.lip_fullness <= 0.035:
            out.append(_feat(feats, "mouth_thin", locale))
    if m.upper_court >= 0.38:
        out.append(_feat(feats, "forehead_high", locale))
    elif m.upper_court <= 0.28:
        out.append(_feat(feats, "forehead_compact", locale))

    return out


def _feat(feats: dict, key: str, locale: str) -> Reading:
    e = feats[key]
    return Reading(
        system="mianxiang", topic=f"features.{key}",
        text=_t(e, locale), source=e["source"],
    )


# Questionnaire answers → KB feature keys (measurable-by-photo traits
# are also here so the no-photo path stands alone).
_ANSWER_MAP: list[tuple] = [
    ("eye_spacing", Spacing.WIDE, "eyes_wide_set"),
    ("eye_spacing", Spacing.CLOSE, "eyes_close_set"),
    ("eye_size", Size.LARGE, "eyes_large"),
    ("eye_size", Size.SMALL, "eyes_small"),
    ("heavy_eyelid", True, "eyelid_heavy"),
    ("steady_gaze", True, "gaze_steady"),
    ("brow_thickness", Fullness.FULL, "brows_thick"),
    ("brow_thickness", Fullness.THIN, "brows_thin"),
    ("nose_fleshy", True, "nose_fleshy"),
    ("nose_fleshy", False, "nose_narrow"),
    ("lip_fullness", Fullness.FULL, "mouth_full"),
    ("lip_fullness", Fullness.THIN, "mouth_thin"),
    ("jaw_wide", True, "jaw_wide"),
    ("jaw_wide", False, "jaw_soft"),
    ("cheeks_full", True, "cheeks_full"),
    ("cheekbones_high", True, "cheekbones_high"),
    ("forehead_high", True, "forehead_high"),
    ("forehead_high", False, "forehead_compact"),
    ("ears_large", True, "ears_large"),
]

_SHAPE_TO_ELEMENT = {
    "round": "water",
    "square": "earth",
    "long": "wood",
    "pointed": "fire",
    "rectangular": "metal",
}


def readings_from_answers(
    answers: FeatureAnswers, locale: str, skip_measurable: bool = False
) -> list[Reading]:
    """Questionnaire path. With `skip_measurable`, only traits that
    geometry cannot see (eyelid, gaze, brows, ears, cheeks) are added
    on top of metric readings."""
    out: list[Reading] = []
    feats = MIANXIANG["features"]

    if answers.face_shape and not skip_measurable:
        el = _SHAPE_TO_ELEMENT[answers.face_shape.value]
        entry = MIANXIANG["five_elements"][el]
        out.append(Reading(
            system="mianxiang", topic=f"five_elements.{el}",
            text=_t(entry["reading"], locale), source=entry["source"],
        ))

    unmeasurable = {"heavy_eyelid", "steady_gaze", "brow_thickness",
                    "ears_large", "cheeks_full", "cheekbones_high",
                    "eye_size"}
    for field, value, kb_key in _ANSWER_MAP:
        if skip_measurable and field not in unmeasurable:
            continue
        if getattr(answers, field, None) == value:
            out.append(_feat(feats, kb_key, locale))
    return out
