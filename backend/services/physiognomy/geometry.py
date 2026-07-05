"""Landmarks → scale-free face metrics. Pure geometry, no interpretation.

Point indices follow the MediaPipe FaceMesh 468-point topology; the
client (browser FaceLandmarker) sends [[x, y], ...] in pixels or
normalized units — all metrics are distance ratios, so units cancel.
"""

from __future__ import annotations

import math

from backend.services.physiognomy.schemas import FaceMetrics

# MediaPipe FaceMesh canonical indices.
FOREHEAD_TOP = 10
CHIN = 152
CHEEK_L, CHEEK_R = 234, 454
JAW_L, JAW_R = 58, 288
BROW_L, BROW_R = 105, 334
EYE_L_OUT, EYE_L_IN = 33, 133
EYE_R_IN, EYE_R_OUT = 362, 263
NOSE_BASE = 2
ALA_L, ALA_R = 98, 327
LIP_TOP, LIP_BOTTOM = 13, 14
LIP_TOP_OUT, LIP_BOTTOM_OUT = 0, 17
MOUTH_L, MOUTH_R = 61, 291

MIN_POINTS = 468


def _d(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


# Yaw gate: head rotation forshortens the visible face width and skews
# every width ratio (live case: W/L 0.64 vs the same person's stable
# 0.85-0.96). A rotated face shows unequal left/right eye widths.
_MAX_EYE_ASYMMETRY = 0.20


def metrics_from_landmarks(pts: list[list[float]]) -> FaceMetrics:
    """Compute FaceMetrics from a FaceMesh point list (>=468 points)."""
    if len(pts) < MIN_POINTS:
        raise ValueError(
            f"Expected >= {MIN_POINTS} FaceMesh landmarks, got {len(pts)}"
        )

    eye_l = _d(pts[EYE_L_OUT], pts[EYE_L_IN])
    eye_r = _d(pts[EYE_R_IN], pts[EYE_R_OUT])
    if max(eye_l, eye_r):
        asym = abs(eye_l - eye_r) / max(eye_l, eye_r)
        if asym > _MAX_EYE_ASYMMETRY:
            raise ValueError(
                f"Face appears rotated (eye-width asymmetry {asym:.2f} > "
                f"{_MAX_EYE_ASYMMETRY}); width ratios would be distorted. "
                "Use a frontal photo."
            )

    face_h = _d(pts[FOREHEAD_TOP], pts[CHIN])
    cheek_w = _d(pts[CHEEK_L], pts[CHEEK_R])
    jaw_w = _d(pts[JAW_L], pts[JAW_R])
    if face_h < 1e-6 or cheek_w < 1e-6:
        raise ValueError(
            "Degenerate landmarks: zero face height or width. "
            "Send real FaceMesh output."
        )

    brow_y = (pts[BROW_L][1] + pts[BROW_R][1]) / 2.0
    # Vertical spans for the three courts (san ting / Lavater storeys).
    upper = abs(brow_y - pts[FOREHEAD_TOP][1])
    middle = abs(pts[NOSE_BASE][1] - brow_y)
    lower = abs(pts[CHIN][1] - pts[NOSE_BASE][1])
    total = upper + middle + lower or 1.0

    eye_w = (_d(pts[EYE_L_OUT], pts[EYE_L_IN]) + _d(pts[EYE_R_IN], pts[EYE_R_OUT])) / 2.0
    inner_canthal = _d(pts[EYE_L_IN], pts[EYE_R_IN])

    fwhr_h = abs(pts[LIP_TOP][1] - brow_y) or 1.0

    # Anatomical lip thickness: vermilion heights (outer→inner mid
    # points) over mouth width. Farkas anthropometry puts the neutral
    # around (8.4 + 9.7) / 53 mm ≈ 0.34. A smile stretches the mouth
    # and thins the vermilion (live case 2026-07-05: 0.18-0.21 smiling
    # vs 0.23-0.31 neutral, same person), so the metric is only
    # trusted on a near-closed mouth: inner gap ≤ 6% of mouth width.
    mouth_w = _d(pts[MOUTH_L], pts[MOUTH_R])
    lip_thickness = None
    if mouth_w > 1e-6:
        inner_gap = _d(pts[LIP_TOP], pts[LIP_BOTTOM])
        if inner_gap / mouth_w <= 0.06:
            vermilion = (_d(pts[LIP_TOP_OUT], pts[LIP_TOP])
                         + _d(pts[LIP_BOTTOM], pts[LIP_BOTTOM_OUT]))
            lip_thickness = round(vermilion / mouth_w, 4)

    return FaceMetrics(
        width_length=round(cheek_w / face_h, 4),
        fwhr=round(cheek_w / fwhr_h, 4),
        jaw_cheek=round(jaw_w / cheek_w, 4),
        eye_spacing=round(inner_canthal / eye_w, 4) if eye_w else 1.0,
        upper_court=round(upper / total, 4),
        middle_court=round(middle / total, 4),
        lower_court=round(lower / total, 4),
        nose_width=round(_d(pts[ALA_L], pts[ALA_R]) / cheek_w, 4),
        lip_fullness=round(_d(pts[LIP_TOP], pts[LIP_BOTTOM]) / face_h, 4),
        lip_thickness=lip_thickness,
    )
