"""Physiognomy reading service (mianxiang + Western traditions).

Reflective/entertainment only. Deterministic geometry first,
cited tradition dictionary second, никакой генерации трактовок.
"""

from backend.services.physiognomy.schemas import (
    FaceMetrics,
    FeatureAnswers,
    PhysiognomyRequest,
    PhysiognomyResponse,
    Reading,
)
from backend.services.physiognomy.service import PhysiognomyService

__all__ = [
    "FaceMetrics",
    "FeatureAnswers",
    "PhysiognomyRequest",
    "PhysiognomyResponse",
    "Reading",
    "PhysiognomyService",
]
