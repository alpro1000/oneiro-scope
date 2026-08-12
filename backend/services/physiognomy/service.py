"""Physiognomy service orchestrator: request → metrics → readings."""

from __future__ import annotations

from typing import Optional

from backend.services.physiognomy import analyzer, geometry
from backend.services.physiognomy.schemas import (
    DISCLAIMER_EN,
    DISCLAIMER_RU,
    TRADITION_CONFIDENCE,
    FaceMetrics,
    PhysiognomyRequest,
    PhysiognomyResponse,
)


class PhysiognomyService:
    def analyze(self, req: PhysiognomyRequest) -> PhysiognomyResponse:
        locale = "en" if req.locale == "en" else "ru"

        metrics: Optional[FaceMetrics] = req.metrics
        metrics_provenance = "supplied ratios" if metrics else None
        if metrics is None and req.landmarks:
            metrics = geometry.metrics_from_landmarks(req.landmarks)
            metrics_provenance = (
                "landmark geometry (MediaPipe FaceMesh indices, "
                "deterministic ratios; confidence 1.0)"
            )

        readings = []
        primary = secondary = court = None
        scores = []
        if metrics is not None:
            scores = analyzer.element_scores(metrics)
            primary, secondary = scores[0].element, scores[1].element
            court = analyzer.dominant_court(metrics)
            readings.extend(analyzer.readings_from_metrics(metrics, locale))
            if req.features:
                readings.extend(analyzer.readings_from_answers(
                    req.features, locale, skip_measurable=True,
                    mouth_measured=metrics.lip_thickness is not None,
                ))
        elif req.features:
            readings.extend(analyzer.readings_from_answers(
                req.features, locale, skip_measurable=False
            ))

        return PhysiognomyResponse(
            metrics=metrics,
            metrics_provenance=metrics_provenance,
            primary_element=primary,
            secondary_element=secondary,
            element_scores=scores,
            dominant_court=court,
            readings=readings,
            disclaimer=DISCLAIMER_RU if locale == "ru" else DISCLAIMER_EN,
            provenance={
                "measurements": "deterministic geometry (1.0)" if metrics else None,
                "interpretations": (
                    f"tradition dictionaries, confidence {TRADITION_CONFIDENCE} "
                    "(below symbol-dictionary tier: physiognomy is not "
                    "scientifically validated)"
                ),
                "traditions": [
                    analyzer.MIANXIANG["_meta"]["tradition"],
                    analyzer.WESTERN["_meta"]["tradition"],
                ],
            },
        )

    @staticmethod
    def methods() -> dict:
        """Supported systems with primary sources and scientific status."""
        return {
            "systems": [
                {
                    "id": "mianxiang",
                    "meta": analyzer.MIANXIANG["_meta"],
                    "components": ["five_elements", "three_courts",
                                   "twelve_palaces", "features"],
                },
                {
                    "id": "western",
                    "meta": analyzer.WESTERN["_meta"],
                    "components": ["lavater_zones", "corman",
                                   "kretschmer", "fwhr_note"],
                },
            ],
            "input_modes": [
                "landmarks (browser MediaPipe FaceLandmarker — photo never leaves the device)",
                "metrics (precomputed ratios)",
                "features (questionnaire, no photo required)",
                "photo upload (server-side, only if CV dependencies installed)",
            ],
            "confidence": {
                "measurements": 1.0,
                "interpretations": TRADITION_CONFIDENCE,
            },
            # WP-13 (additive): the same split, named rather than scored.
            "rule_source_tier": {
                "measurements": "computed",
                "interpretations": "unvalidated_tradition",
            },
        }
