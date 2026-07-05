"""Frame-set aggregation: a photo archive → one stable profile.

Median metrics over the accepted frames (expression outliers cancel),
KB readings for the median, and per-topic `support` — the share of
frames whose OWN readings contain the topic. Support is a 1.0-tier
fact about cross-frame agreement; the interpretation tier stays 0.6.

The coverage map states explicitly what was measured, what only the
questionnaire can add, what would need a guided scan, and what is
unreadable from casual photos in principle — so "determine the
maximum" never silently becomes "invent the rest".
"""

from __future__ import annotations

import statistics
from typing import Optional

from backend.services.physiognomy import analyzer
from backend.services.physiognomy.longitudinal import median_metrics
from backend.services.physiognomy.schemas import (
    FaceMetrics,
    FeatureAnswers,
    PhysiognomyRequest,
)
from backend.services.physiognomy.service import PhysiognomyService

# Static coverage knowledge — what each acquisition mode can honestly
# provide. Evidence for the "unreadable" class: 2026-07-05 experiments
# (palace-zone texture ×26 spread after within-frame normalization;
# child-skin control indistinguishable from adult), soul.md §9.
_COVERAGE = {
    "ru": {
        "measured": (
            "форма и пропорции (5 элементов, 3 двора, fWHR, расстановка "
            "глаз, лоб, челюсть, нос-форма, толщина губ на закрытом рте)"
        ),
        "questionnaire_only": (
            "веко, взгляд, брови, уши, щёки, скулы — надёжной "
            "FaceMesh-эвристики нет, только анкета"
        ),
        "guided_scan_only": (
            "дух глаз (шэнь — нужно видео), текстура дворцов — возможно, "
            "при управляемой съёмке с ровным светом (не доказано)"
        ),
        "unreadable": (
            "цвет ци-сэ и гладкость дворцов по бытовым фото: доказано "
            "нечитаемо (разброс ×26 после нормировки; детский контроль "
            "не отличим от взрослого)"
        ),
    },
    "en": {
        "measured": (
            "shape and proportions (five elements, three courts, fWHR, "
            "eye spacing, forehead, jaw, nose shape, closed-mouth lip "
            "thickness)"
        ),
        "questionnaire_only": (
            "eyelid, gaze, brows, ears, cheeks, cheekbones — no reliable "
            "FaceMesh heuristic, questionnaire only"
        ),
        "guided_scan_only": (
            "shen of the eyes (needs video), palace texture — possibly "
            "under guided even-light capture (unproven)"
        ),
        "unreadable": (
            "qi-se color and palace smoothness from casual photos: "
            "proven unreadable (×26 spread after normalization; child-"
            "skin control indistinguishable from adult)"
        ),
    },
}


def _stability(frames: list[FaceMetrics]) -> dict:
    """Per-metric cross-frame spread; 'stable' ≤ 10% of the median."""
    out = {}
    for field in FaceMetrics.model_fields:
        vals = [getattr(f, field) for f in frames if getattr(f, field) is not None]
        if len(vals) < 2:
            continue
        med = statistics.median(vals)
        spread = max(vals) - min(vals)
        out[field] = {
            "median": round(med, 4),
            "spread": round(spread, 4),
            "frames": len(vals),
            "stable": bool(med and spread / abs(med) <= 0.10),
        }
    return out


def analyze_frames(
    frames: list[FaceMetrics],
    features: Optional[FeatureAnswers] = None,
    locale: str = "ru",
) -> dict:
    """Aggregate a set of per-frame metrics into one profile."""
    if not frames:
        raise ValueError("Need at least one FaceMetrics frame")
    loc = "en" if locale == "en" else "ru"

    median = median_metrics(frames)
    resp = PhysiognomyService().analyze(PhysiognomyRequest(
        metrics=median, features=features, locale=loc,
    ))

    # Support: how many frames' own readings contain each topic. For
    # topics built on optional metrics the denominator is the frames
    # that could measure them at all (e.g. lips need a closed mouth) —
    # "5/5 measurable" is the honest count, not "5/11 total".
    per_frame_topics = [
        {r.topic for r in analyzer.readings_from_metrics(f, loc)}
        for f in frames
    ]
    optional_metric = {"features.mouth_thin": "lip_thickness",
                       "features.mouth_full": "lip_thickness",
                       "features.nose_fleshy": "nose_width"}
    readings = []
    for r in resp.readings:
        item = r.model_dump()
        if r.topic.startswith(("features.", "five_elements.", "three_courts.",
                               "lavater_zones.", "corman.", "kretschmer.",
                               "fwhr.")):
            n = sum(1 for topics in per_frame_topics if r.topic in topics)
            metric = optional_metric.get(r.topic)
            denom = (sum(1 for f in frames if getattr(f, metric) is not None)
                     if metric else len(frames))
            # Questionnaire-sourced readings never appear in frame
            # topics — report support only for geometry-backed ones.
            if n:
                item["support"] = f"{n}/{denom}"
        readings.append(item)

    primaries = [analyzer.element_scores(f)[0].element for f in frames]
    consensus = {e: primaries.count(e) for e in dict.fromkeys(primaries)}

    return {
        "frames_used": len(frames),
        "metrics": median.model_dump(),
        "stability": _stability(frames),
        "primary_element": resp.primary_element,
        "secondary_element": resp.secondary_element,
        "element_consensus": consensus,
        "element_scores": [e.model_dump() for e in resp.element_scores],
        "dominant_court": resp.dominant_court,
        "readings": readings,
        "coverage": _COVERAGE[loc],
        "provenance": {
            **resp.provenance,
            "aggregation": (
                "per-metric medians over frames; support = share of "
                "frames whose own readings contain the topic (1.0-tier "
                "fact; interpretation tier unchanged)"
            ),
        },
        "disclaimer": resp.disclaimer,
    }
