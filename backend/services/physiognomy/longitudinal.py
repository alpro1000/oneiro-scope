"""Longitudinal comparison: early-period frames vs later-period frames.

Deterministic throughout: per-metric medians over each period's frames
(single frames carry expression noise; the median is the stable face),
then the same KB readings for both medians, diffed by topic. Every text
still comes from the tradition dictionaries — composition only.

Caveat carried in every result: the KB thresholds are adult
anthropometry (neutral W/L ≈ 0.72). A child's face is naturally wider
and rounder, so childhood-period readings are a stability probe for
traits, not a standalone portrait.
"""

from __future__ import annotations

import statistics

from backend.services.physiognomy import analyzer
from backend.services.physiognomy.schemas import (
    DISCLAIMER_EN,
    DISCLAIMER_RU,
    FaceMetrics,
)

_ADULT_KB_NOTE = {
    "ru": (
        "Пороги словарей — взрослая антропометрия; детское лицо шире и "
        "круглее от природы, поэтому ранний период — проверка "
        "устойчивости черт, а не самостоятельный портрет."
    ),
    "en": (
        "KB thresholds are adult anthropometry; a child's face is "
        "naturally wider and rounder, so the early period probes trait "
        "stability rather than standing alone as a portrait."
    ),
}


def median_metrics(frames: list[FaceMetrics]) -> FaceMetrics:
    """Per-field medians; optional fields use only frames that have them."""
    if not frames:
        raise ValueError("Need at least one FaceMetrics frame")
    data = {}
    for field in FaceMetrics.model_fields:
        vals = [getattr(f, field) for f in frames if getattr(f, field) is not None]
        data[field] = round(statistics.median(vals), 4) if vals else None
    return FaceMetrics(**data)


def _period_summary(median: FaceMetrics, locale: str) -> dict:
    scores = analyzer.element_scores(median)
    return {
        "metrics": median.model_dump(),
        "primary_element": scores[0].element,
        "secondary_element": scores[1].element,
        "element_scores": [s.model_dump() for s in scores],
        "dominant_court": analyzer.dominant_court(median),
        "readings": [r.model_dump() for r in
                     analyzer.readings_from_metrics(median, locale)],
    }


def compare_periods(
    early: list[FaceMetrics], later: list[FaceMetrics], locale: str = "ru"
) -> dict:
    """Diff the KB readings of two life periods.

    Topics present in both medians are `stable` (the trait survived the
    years between the periods); `appeared`/`disappeared` hold the
    later-only and early-only readings.
    """
    loc = "en" if locale == "en" else "ru"
    e, l = _period_summary(median_metrics(early), loc), _period_summary(
        median_metrics(later), loc)

    e_topics = {r["topic"]: r for r in e["readings"]}
    l_topics = {r["topic"]: r for r in l["readings"]}
    keep = ("topic", "system", "text", "source", "confidence")

    def slim(r: dict) -> dict:
        return {k: r[k] for k in keep}

    deltas = {}
    for field in FaceMetrics.model_fields:
        ev, lv = e["metrics"][field], l["metrics"][field]
        if ev is not None and lv is not None:
            deltas[field] = round(lv - ev, 4)

    return {
        "early": e,
        "later": l,
        "metric_deltas": deltas,
        "stable": [slim(l_topics[t]) for t in l_topics if t in e_topics],
        "appeared": [slim(l_topics[t]) for t in l_topics if t not in e_topics],
        "disappeared": [slim(e_topics[t]) for t in e_topics if t not in l_topics],
        "frames_used": {"early": len(early), "later": len(later)},
        "note": _ADULT_KB_NOTE[loc],
        "provenance": {
            "measurements": "per-period medians of deterministic geometry (1.0)",
            "interpretations": "tradition dictionaries (0.6), diffed by topic",
        },
        "disclaimer": DISCLAIMER_RU if loc == "ru" else DISCLAIMER_EN,
    }
