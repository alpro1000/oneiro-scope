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
import uuid
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


def _safe_roots(*candidates: Path) -> tuple[Path, ...]:
    """Drop any candidate that IS a filesystem anchor: if a root
    resolves to '/', is_relative_to() passes for everything and the
    confinement silently dies (deployment with cwd='/')."""
    return tuple(p for p in candidates if p != Path(p.anchor))


# Project root from code location, NOT runtime cwd — cwd is
# deployment-dependent and may be '/'.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Report files may only land under these roots — MCP can run as a
# remote HTTP server, so an arbitrary output_path would be a path-
# traversal write primitive (CWE-22).
_ALLOWED_REPORT_ROOTS = _safe_roots(
    Path(tempfile.gettempdir()).resolve(),
    _PROJECT_ROOT,
)

# Reading photos is likewise confined: in HTTP mode an arbitrary
# photo_path lets a remote caller probe the server filesystem. Home
# covers the local-desktop use case (photos in ~/...).
_ALLOWED_READ_ROOTS = _safe_roots(
    Path.home().resolve(),
    Path(tempfile.gettempdir()).resolve(),
    _PROJECT_ROOT,
)


def _safe_report_path(output_path: Optional[str]) -> Path:
    if not output_path:  # None or "" — both mean "use the default"
        # %f + uuid suffix: concurrent calls must never collide.
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        name = f"physiognomy_report_{stamp}_{uuid.uuid4().hex[:8]}.html"
        return Path(tempfile.gettempdir()) / name
    path = Path(output_path).resolve()
    if not any(path.is_relative_to(root) for root in _ALLOWED_REPORT_ROOTS):
        allowed = ", ".join(str(r) for r in _ALLOWED_REPORT_ROOTS)
        raise ValueError(
            f"output_path must stay under: {allowed} (got {path})"
        )
    if path.is_dir():
        raise ValueError(f"output_path is a directory: {path}")
    return path


def _analyze(
    landmarks: Optional[list[list[float]]],
    metrics: Optional[dict],
    features: Optional[dict],
    photo_path: Optional[str],
    locale: str,
) -> PhysiognomyResponse:
    if photo_path:
        landmarks = _landmarks_from_photo(photo_path)
    if not (landmarks or metrics or features):
        raise ValueError(
            "Provide at least one of: landmarks, metrics, features, photo_path"
        )
    return _svc().analyze(PhysiognomyRequest(
        landmarks=landmarks,
        metrics=FaceMetrics(**metrics) if metrics else None,
        features=FeatureAnswers(**features) if features else None,
        locale=locale,
    ))


def _landmarks_from_photo(photo_path: str) -> list[list[float]]:
    """Local-file CV path. Requires the optional mediapipe dependency."""
    resolved = Path(photo_path).resolve()
    if not any(resolved.is_relative_to(r) for r in _ALLOWED_READ_ROOTS):
        raise ValueError(
            "photo_path must stay under the home, temp or project directory"
        )
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

    path = _safe_report_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
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
