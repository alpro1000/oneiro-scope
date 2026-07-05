"""Pydantic contracts for the physiognomy service.

Reflective/entertainment reading of facial-feature traditions
(mianxiang + Western schools). Measurements are deterministic
geometry (confidence 1.0); interpretations are a cited tradition
dictionary (confidence 0.6 — deliberately BELOW the 0.8
symbol-dictionary tier: physiognomy has no scientific validity).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# Tradition-dictionary tier. Single place to change.
TRADITION_CONFIDENCE = 0.6

DISCLAIMER_RU = (
    "Рефлексивно-развлекательное чтение по историческим традициям "
    "(мянсян, Лафатер, Корман, Кречмер). Физиогномика научно не "
    "валидирована (Todorov, 'Face Value', 2017): устойчивые черты "
    "личности по лицу не читаются. Только для само-рефлексии "
    "владельца фото; запрещено применять для оценки других людей, "
    "найма, кредитных или правовых решений. Не содержит суждений о "
    "здоровье и внешности."
)
DISCLAIMER_EN = (
    "Reflective/entertainment reading based on historical traditions "
    "(mianxiang, Lavater, Corman, Kretschmer). Physiognomy is not "
    "scientifically validated (Todorov, 'Face Value', 2017): stable "
    "personality traits cannot be read from faces. Self-reflection "
    "only, for the photo's owner; must not be used to judge other "
    "people, for hiring, credit or legal decisions. Contains no "
    "health or attractiveness judgments."
)


class FaceShape(str, Enum):
    ROUND = "round"
    SQUARE = "square"
    LONG = "long"
    POINTED = "pointed"          # wide forehead, narrow chin
    RECTANGULAR = "rectangular"


class Spacing(str, Enum):
    WIDE = "wide"
    AVERAGE = "average"
    CLOSE = "close"


class Size(str, Enum):
    LARGE = "large"
    AVERAGE = "average"
    SMALL = "small"


class Fullness(str, Enum):
    FULL = "full"
    AVERAGE = "average"
    THIN = "thin"


class FeatureAnswers(BaseModel):
    """Questionnaire fallback — the no-photo path. Every field is
    optional; only answered features produce readings."""

    face_shape: Optional[FaceShape] = None
    eye_spacing: Optional[Spacing] = None
    eye_size: Optional[Size] = None
    heavy_eyelid: Optional[bool] = None
    steady_gaze: Optional[bool] = None
    brow_thickness: Optional[Fullness] = None
    nose_fleshy: Optional[bool] = None
    lip_fullness: Optional[Fullness] = None
    jaw_wide: Optional[bool] = None
    cheeks_full: Optional[bool] = None
    cheekbones_high: Optional[bool] = None
    forehead_high: Optional[bool] = None
    ears_large: Optional[bool] = None


class FaceMetrics(BaseModel):
    """Scale-free ratios computed from landmarks (or supplied directly).

    All are ratios of pixel distances, so camera distance and image
    size cancel out.
    """

    width_length: float = Field(..., description="bizygomatic width / face height (10→152)")
    fwhr: float = Field(..., description="bizygomatic width / brow-to-upper-lip height")
    jaw_cheek: float = Field(..., description="gonial (jaw) width / bizygomatic width")
    eye_spacing: float = Field(..., description="inner-canthal distance / eye width")
    upper_court: float = Field(..., description="forehead height share of face height")
    middle_court: float = Field(..., description="midface height share")
    lower_court: float = Field(..., description="lower face height share")
    nose_width: Optional[float] = Field(None, description="alar width / bizygomatic width")
    lip_fullness: Optional[float] = Field(None, description="lip height / face height")


class PhysiognomyRequest(BaseModel):
    """Input priority: metrics > landmarks > features. Features also
    supplement non-measurable traits (eyelid, gaze) in any mode."""

    landmarks: Optional[list[list[float]]] = Field(
        None, description="MediaPipe FaceMesh points [[x,y],...] (468+), pixels or normalized"
    )
    metrics: Optional[FaceMetrics] = None
    features: Optional[FeatureAnswers] = None
    locale: str = "ru"


class Reading(BaseModel):
    """One traditional interpretation with mandatory provenance."""

    system: str          # "mianxiang" | "lavater" | "corman" | "kretschmer" | "fwhr"
    topic: str           # e.g. "five_elements.earth", "features.jaw_wide"
    text: str
    source: str
    confidence: float = TRADITION_CONFIDENCE


class ElementScore(BaseModel):
    element: str
    score: float


class MethodsSystem(BaseModel):
    id: str
    meta: dict
    components: list[str]


class MethodsResponse(BaseModel):
    systems: list[MethodsSystem]
    input_modes: list[str]
    confidence: dict


class PhysiognomyResponse(BaseModel):
    metrics: Optional[FaceMetrics] = None
    metrics_provenance: Optional[str] = None
    primary_element: Optional[str] = None
    secondary_element: Optional[str] = None
    element_scores: list[ElementScore] = []
    dominant_court: Optional[str] = None
    readings: list[Reading]
    disclaimer: str
    provenance: dict
