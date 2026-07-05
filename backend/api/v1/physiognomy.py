"""Physiognomy API endpoints (reflective/entertainment face reading)."""

from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.services.physiognomy import (
    FeatureAnswers,
    PhysiognomyRequest,
    PhysiognomyResponse,
    PhysiognomyService,
)
from backend.services.physiognomy.schemas import MethodsResponse

router = APIRouter(prefix="/physiognomy", tags=["physiognomy"])

# Upload cap: a face photo has no business being larger than this;
# without a limit the decode path is a trivial memory/CPU DoS.
MAX_PHOTO_BYTES = 8 * 1024 * 1024

# Frame cap for the archive endpoint: the guided scanner sends ~5;
# anything past this is abuse, not a face archive.
MAX_ARCHIVE_FRAMES = 24


class ArchiveRequest(BaseModel):
    """A set of landmark frames from the same person (guided scanner
    or browser-extracted photo archive). Photos never travel — only
    468-point coordinate lists."""

    frames: list[list[list[float]]] = Field(
        ..., min_length=1, max_length=MAX_ARCHIVE_FRAMES,
        description="FaceMesh landmark sets, one per captured frame",
    )
    features: Optional[FeatureAnswers] = None
    locale: str = "ru"


class ArchiveResponse(BaseModel):
    """Aggregated profile: median metrics, stability, readings with
    cross-frame support, coverage map, skip reasons."""

    frames_used: int
    skipped: list[str]
    metrics: dict
    traits: list[dict] = []
    signature: list[dict] = []
    lens_note: str = ""
    stability: dict
    primary_element: Optional[str] = None
    secondary_element: Optional[str] = None
    element_consensus: dict
    element_scores: list[dict]
    dominant_court: Optional[str] = None
    readings: list[dict]
    coverage: dict
    provenance: dict
    disclaimer: str


def get_service() -> PhysiognomyService:
    return PhysiognomyService()


@router.get(
    "/methods",
    response_model=MethodsResponse,
    summary="Supported face-reading systems",
    description="Traditions, primary sources, scientific status and input modes.",
)
async def methods() -> MethodsResponse:
    return MethodsResponse(**PhysiognomyService.methods())


@router.post(
    "/analyze",
    response_model=PhysiognomyResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze face landmarks / metrics / questionnaire",
    description="""
    Reflective/entertainment reading (mianxiang + Western traditions).

    **Privacy-first flow:** extract 468 FaceMesh landmarks in the
    browser (MediaPipe FaceLandmarker) and send only coordinates —
    the photo never leaves the device. Alternatively send precomputed
    `metrics` or a `features` questionnaire (no photo at all).

    Self-reflection only: analyze your own face, never third parties.
    """,
)
async def analyze(request: PhysiognomyRequest) -> PhysiognomyResponse:
    if not (request.landmarks or request.metrics or request.features):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide landmarks, metrics or features",
        )
    try:
        return get_service().analyze(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post(
    "/analyze-archive",
    response_model=ArchiveResponse,
    summary="Aggregate a set of landmark frames into one stable profile",
    description="""
    The archive/scanner twin of /analyze: every frame passes the
    quality gates (rejects recorded with reasons, not fatal), the
    accepted ones are aggregated — median metrics, cross-frame
    stability, per-reading `support` — and the coverage map states
    what was measured vs what needs the questionnaire, a guided scan,
    or is unreadable from photos in principle.

    Privacy-first: send landmark coordinates only, never the photos.
    Self-reflection only: analyze your own face, never third parties.
    """,
)
async def analyze_archive(request: ArchiveRequest) -> ArchiveResponse:
    from backend.services.physiognomy.aggregate import analyze_frames
    from backend.services.physiognomy.geometry import metrics_from_landmarks

    frames, skipped = [], []
    for i, lms in enumerate(request.frames):
        try:
            frames.append(metrics_from_landmarks(lms))
        except ValueError as exc:
            skipped.append(f"frame {i}: {exc}")
    if not frames:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No usable frames — all rejected: " + "; ".join(skipped),
        )
    result = analyze_frames(frames, features=request.features,
                            locale=request.locale)
    result["skipped"] = skipped
    return ArchiveResponse(**result)


@router.post(
    "/analyze-photo",
    response_model=PhysiognomyResponse,
    summary="Analyze an uploaded photo (server-side CV, optional)",
    description="""
    Server-side landmark extraction. Requires the optional `mediapipe`
    dependency; without it returns 501 pointing to the client-side
    flow. The image is processed in memory and never stored.
    """,
)
async def analyze_photo(
    file: UploadFile = File(...), locale: str = "ru"
) -> PhysiognomyResponse:
    try:
        import mediapipe as mp  # optional heavy dependency
        import numpy as np
        import cv2
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Server-side CV is not installed. Use the client-side flow: "
                "extract FaceMesh landmarks in the browser and POST them to "
                "/physiognomy/analyze, or send the features questionnaire."
            ),
        ) from exc

    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Expected an image upload, got {file.content_type}",
        )
    data = await file.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Photo exceeds {MAX_PHOTO_BYTES // (1024 * 1024)} MB limit",
        )
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Empty upload")
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Not an image")

    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=1, refine_landmarks=False
    ) as mesh:
        res = mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if not res.multi_face_landmarks:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No face found")

    h, w = img.shape[:2]
    pts = [[lm.x * w, lm.y * h] for lm in res.multi_face_landmarks[0].landmark]
    return get_service().analyze(
        PhysiognomyRequest(landmarks=pts, locale=locale)
    )
