"""Physiognomy MCP tools.

Wraps `backend.services.physiognomy` for agents/skills: analysis from
landmarks/metrics/questionnaire, optional local-photo path (server CV),
tradition/method listing, and an HTML report written to a file.

Reflective/entertainment only — every reading carries its source and
the 0.6 tradition-tier confidence; the disclaimer travels in every
response and report.
"""

from __future__ import annotations

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


# Path safety lives in the shared module (hardened across PR #136-#139);
# re-exported here for backward compatibility with existing tests.
from backend.mcp.tools._files import (  # noqa: E402
    _PROJECT_ROOT,
    _resolve_user_path,
    _safe_roots,
    write_report,
)
from backend.mcp.tools._files import _safe_read_path as _photo_path_guard
from backend.mcp.tools._files import _safe_report_path as _files_safe_report_path


def _safe_report_path(output_path):
    """Back-compat wrapper with the physiognomy default prefix."""
    return _files_safe_report_path(output_path, "physiognomy_report")


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


def _detect(mesh, cv2, img) -> Optional[list[list[float]]]:
    res = mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if not res.multi_face_landmarks:
        return None
    h, w = img.shape[:2]
    return [[lm.x * w, lm.y * h] for lm in res.multi_face_landmarks[0].landmark]


# Refinement target: FaceMesh landmark precision degrades on small
# faces (distant subject, archival scans). Once a face is found, the
# face box is cropped with margin and upscaled to this height for a
# second, sharper pass. All metrics are ratios, so crop-space
# coordinates are as valid as image-space ones.
_ZOOM_FACE_H = 600.0
_ZOOM_MARGIN = 0.3

def _landmarks_from_photo(photo_path: str) -> list[list[float]]:
    """Local-file CV path with auto-zoom. Requires optional mediapipe.

    Detection ladder: native image → 2x/3x upscale (small or low-
    contrast faces, e.g. archival prints) → after any hit, a cropped
    and enlarged second pass over the face box refines the landmarks.
    """
    resolved = _photo_path_guard(photo_path, what="photo_path")
    try:
        import cv2
        import mediapipe as mp
    except ImportError as exc:
        raise RuntimeError(
            "Server-side CV is not installed (pip install mediapipe "
            "opencv-python-headless). Send `landmarks` extracted client-side "
            "or a `features` questionnaire instead."
        ) from exc

    img = cv2.imread(str(resolved))
    if img is None:
        raise ValueError(f"Cannot read image: {photo_path}")

    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=1
    ) as mesh:
        pts = _detect(mesh, cv2, img)
        base = img
        for scale in (2, 3):
            if pts is not None:
                break
            if max(img.shape[:2]) * scale > 6000:  # keep memory sane
                break
            base = cv2.resize(img, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_CUBIC)
            pts = _detect(mesh, cv2, base)
        if pts is None:
            raise ValueError("No face found (check pose, glasses, distance)")

        # Second pass: zoom into the face box and re-detect for
        # sharper landmarks; fall back to the first pass if it misses.
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        h, w = base.shape[:2]
        mx = (max(xs) - min(xs)) * _ZOOM_MARGIN
        my = (max(ys) - min(ys)) * _ZOOM_MARGIN
        x0, x1 = max(0, int(min(xs) - mx)), min(w, int(max(xs) + mx))
        y0, y1 = max(0, int(min(ys) - my)), min(h, int(max(ys) + my))
        face_h = max(ys) - min(ys)
        if x1 > x0 and y1 > y0 and 0 < face_h < _ZOOM_FACE_H:
            zoom = _ZOOM_FACE_H / face_h
            crop = cv2.resize(base[y0:y1, x0:x1], None, fx=zoom, fy=zoom,
                              interpolation=cv2.INTER_CUBIC)
            refined = _detect(mesh, cv2, crop)
            if refined is not None:
                return refined
        return pts


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

    path = write_report(html, output_path, prefix="physiognomy_report")

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


def _period_metrics(
    photo_paths: Optional[list[str]], metrics: Optional[list[dict]], label: str
) -> tuple[list["FaceMetrics"], list[str]]:
    """Collect FaceMetrics for one life period; unusable photos are
    skipped with the reason recorded, not fatal (archival sets always
    contain rotated/undetectable frames)."""
    from backend.services.physiognomy.geometry import metrics_from_landmarks

    frames: list[FaceMetrics] = []
    skipped: list[str] = []
    for p in photo_paths or []:
        try:
            frames.append(metrics_from_landmarks(_landmarks_from_photo(p)))
        except (ValueError, RuntimeError) as exc:
            skipped.append(f"{p}: {exc}")
    frames.extend(FaceMetrics(**m) for m in metrics or [])
    if not frames:
        raise ValueError(
            f"No usable frames for the {label} period"
            + (f" — all skipped: {'; '.join(skipped)}" if skipped else "")
        )
    return frames, skipped


async def analyze_face_archive(
    photo_paths: Optional[list[str]] = None,
    metrics_list: Optional[list[dict]] = None,
    features: Optional[dict] = None,
    locale: str = "ru",
) -> dict[str, Any]:
    """Extract the maximum a photo SET can honestly give: every photo
    goes through the auto-zoom detection ladder, unusable frames are
    skipped with reasons, the rest are aggregated (median metrics,
    cross-frame stability, per-reading `support`), and a coverage map
    states what was measured vs what needs the questionnaire, a guided
    scan, or is unreadable from casual photos in principle.

    Self-reflection only, for the photo owner's own archive.

    Args:
        photo_paths: local images (mixed quality welcome — gates sort
            them out).
        metrics_list: precomputed FaceMetrics dicts — alternative or
            addition to photos.
        features: questionnaire dict supplementing unmeasured traits.
        locale: "ru" or "en".
    """
    from backend.services.physiognomy.aggregate import analyze_frames

    frames, skipped = _period_metrics(photo_paths, metrics_list, "archive")
    result = analyze_frames(
        frames,
        features=FeatureAnswers(**features) if features else None,
        locale=locale,
    )
    result["skipped"] = skipped
    return result


async def physiognomy_timeline(
    early_photo_paths: Optional[list[str]] = None,
    later_photo_paths: Optional[list[str]] = None,
    early_metrics: Optional[list[dict]] = None,
    later_metrics: Optional[list[dict]] = None,
    locale: str = "ru",
) -> dict[str, Any]:
    """Compare two life periods (e.g. childhood vs adulthood) of the
    SAME person: per-period medians of deterministic geometry, then the
    tradition readings diffed by topic — which traits stayed stable
    across the years, which appeared, which faded.

    Self-reflection only, for the photo owner's own archive.

    Args:
        early_photo_paths / later_photo_paths: local images per period
            (auto-zoom detection; unusable frames are skipped, reasons
            reported in `skipped`).
        early_metrics / later_metrics: precomputed FaceMetrics dicts —
            alternative or addition to photos.
        locale: "ru" or "en".
    """
    from backend.services.physiognomy.longitudinal import compare_periods

    early, skipped_e = _period_metrics(early_photo_paths, early_metrics, "early")
    later, skipped_l = _period_metrics(later_photo_paths, later_metrics, "later")
    result = compare_periods(early, later, locale)
    result["skipped"] = {"early": skipped_e, "later": skipped_l}
    return result
