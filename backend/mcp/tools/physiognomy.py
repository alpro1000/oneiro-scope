"""Physiognomy MCP tools.

Wraps `backend.services.physiognomy` for agents/skills: analysis from
landmarks/metrics/questionnaire, optional local-photo path (server CV),
tradition/method listing, and an HTML report written to a file.

Reflective/entertainment only — every reading carries its source and
the 0.6 tradition-tier confidence; the disclaimer travels in every
response and report.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from backend.services.physiognomy.report import render_html
from backend.services.physiognomy.schemas import (
    FaceMetrics,
    FeatureAnswers,
    PhysiognomyRequest,
    PhysiognomyResponse,
)
from backend.services.physiognomy.service import PhysiognomyService

_service: Optional[PhysiognomyService] = None


def _svc() -> PhysiognomyService:
    global _service
    if _service is None:
        _service = PhysiognomyService()
    return _service


def _analyze(
    landmarks: Optional[list[list[float]]],
    metrics: Optional[dict],
    features: Optional[dict],
    photo_path: Optional[str],
    locale: str,
) -> PhysiognomyResponse:
    if photo_path:
        landmarks = _landmarks_from_photo(photo_path)
    return _svc().analyze(PhysiognomyRequest(
        landmarks=landmarks,
        metrics=FaceMetrics(**metrics) if metrics else None,
        features=FeatureAnswers(**features) if features else None,
        locale=locale,
    ))


def _landmarks_from_photo(photo_path: str) -> list[list[float]]:
    """Local-file CV path. Requires the optional mediapipe dependency."""
    try:
        import cv2
        import mediapipe as mp
    except ImportError as exc:
        raise RuntimeError(
            "Server-side CV is not installed (pip install mediapipe "
            "opencv-python-headless). Send `landmarks` extracted client-side "
            "or a `features` questionnaire instead."
        ) from exc

    img = cv2.imread(photo_path)
    if img is None:
        raise ValueError(f"Cannot read image: {photo_path}")
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=1
    ) as mesh:
        res = mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if not res.multi_face_landmarks:
        raise ValueError("No face found (check pose, glasses, distance)")
    h, w = img.shape[:2]
    return [[lm.x * w, lm.y * h] for lm in res.multi_face_landmarks[0].landmark]


async def analyze_face(
    landmarks: Optional[list[list[float]]] = None,
    metrics: Optional[dict] = None,
    features: Optional[dict] = None,
    photo_path: Optional[str] = None,
    locale: str = "ru",
) -> dict[str, Any]:
    """Reflective face reading (mianxiang + Western traditions).

    Deterministic geometry first (FaceMesh landmarks → scale-free ratios,
    confidence 1.0), cited tradition dictionary second (confidence 0.6 —
    physiognomy is not scientifically validated; the disclaimer is in the
    response). Self-reflection only — never analyze third parties.

    Args:
        landmarks: 468+ FaceMesh points [[x, y], ...] (browser-extracted).
        metrics: Precomputed ratios (see FaceMetrics fields).
        features: Questionnaire dict (face_shape, eye_spacing, heavy_eyelid,
            steady_gaze, brow_thickness, nose_fleshy, lip_fullness, jaw_wide,
            cheeks_full, cheekbones_high, forehead_high, ears_large).
        photo_path: Local image path; requires server CV (mediapipe).
        locale: "ru" or "en".
    """
    return _analyze(landmarks, metrics, features, photo_path, locale).model_dump()


async def physiognomy_report(
    landmarks: Optional[list[list[float]]] = None,
    metrics: Optional[dict] = None,
    features: Optional[dict] = None,
    photo_path: Optional[str] = None,
    locale: str = "ru",
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """Run the face reading AND write a self-contained HTML report file
    (print-to-PDF ready). Returns the file path plus a short summary.

    Args: same as analyze_face, plus:
        output_path: Where to write the .html; default — a timestamped
            file in the system temp directory.
    """
    resp = _analyze(landmarks, metrics, features, photo_path, locale)
    html = render_html(resp, locale=locale)

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = Path(tempfile.gettempdir()) / f"physiognomy_report_{stamp}.html"
    path.write_text(html, encoding="utf-8")

    return {
        "report_path": str(path),
        "primary_element": resp.primary_element,
        "secondary_element": resp.secondary_element,
        "dominant_court": resp.dominant_court,
        "readings_count": len(resp.readings),
        "disclaimer": resp.disclaimer,
    }


async def physiognomy_methods() -> dict[str, Any]:
    """List supported face-reading systems with primary sources,
    scientific status, input modes and confidence tiers."""
    return PhysiognomyService.methods()
