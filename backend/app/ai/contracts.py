from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    LOGO = "logo"
    LAYOUT = "layout"
    COLOUR = "colour"
    TYPOGRAPHY = "typography"
    TEXTURE = "texture"
    SHAPE = "shape"
    SEAL = "seal"
    PRINT = "print"
    PACKAGING = "packaging"
    OCR = "ocr"
    BARCODE = "barcode"
    QR = "qr"
    CERTIFICATION = "certification"


class DecisionState(str, Enum):
    LIKELY_GENUINE = "LIKELY_GENUINE"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL_RISK = "CRITICAL_RISK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNSUPPORTED_PRODUCT = "UNSUPPORTED_PRODUCT"
    TAMPERED_OR_DAMAGED = "TAMPERED_OR_DAMAGED"


class RegionBox(BaseModel):
    x_min: float = Field(ge=0.0, le=1.0)
    y_min: float = Field(ge=0.0, le=1.0)
    x_max: float = Field(ge=0.0, le=1.0)
    y_max: float = Field(ge=0.0, le=1.0)
    label: str | None = None
    difference_score: float | None = None
    explanation: str | None = None


class EvidenceObject(BaseModel):
    id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    type: EvidenceType
    score: float | None = Field(default=None, ge=0.0, le=1.0) # 1.0 = match/genuine, 0.0 = total mismatch, None if unavailable
    confidence: float = Field(ge=0.0, le=1.0)     # Model certainty in assessment
    availability: bool = True                     # Was feature detectable in image
    quality: float = Field(default=1.0, ge=0.0, le=1.0) # Region clarity
    source: str                                   # Engine identifier
    reference_id: str | None = None
    model_version: str = "v1.0"
    features: dict[str, Any] = Field(default_factory=dict)
    regions: list[RegionBox] = Field(default_factory=list)
    explanation: str
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


EvidenceResult = EvidenceObject


class QualityAssessmentResult(BaseModel):
    resolution_score: float
    blur_score: float
    brightness_score: float
    contrast_score: float
    glare_score: float
    occlusion_score: float
    overall_quality: float
    usable: bool
    reasons: list[str] = []
    guidance: str | None = None


class DetectedProductBox(BaseModel):
    bbox: tuple[float, float, float, float] # (ymin, xmin, ymax, xmax) normalized
    confidence: float
    aspect_ratio: float


class PackagingFingerprint(BaseModel):
    product_identity: dict[str, Any] = Field(default_factory=dict)
    visual: dict[str, Any] = Field(default_factory=dict)
    text: dict[str, Any] = Field(default_factory=dict)
    machine_readable: dict[str, Any] = Field(default_factory=dict)
    packaging: dict[str, Any] = Field(default_factory=dict)
    regions: list[dict[str, Any]] = Field(default_factory=list)
    version: str = "1.0"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DecisionResult(BaseModel):
    state: DecisionState
    risk_score: float           # 0 to 100
    confidence: float           # 0.0 to 1.0
    uncertainty: float          # 0.0 to 1.0
    evidence_coverage: float    # 0.0 to 1.0
    recommendation: str
    reason_codes: list[str] = []
    explanation_summary: str
    contradictions: list[str] = []
    suspicious_regions: list[RegionBox] = []


# Engine Abstract Interfaces
class BaseImageQualityEngine(ABC):
    @abstractmethod
    def assess(self, image_bgr: np.ndarray) -> QualityAssessmentResult:
        pass


class BaseProductDetector(ABC):
    @abstractmethod
    def detect(self, image_bgr: np.ndarray) -> tuple[DetectedProductBox, np.ndarray]:
        """Returns (detection_box, cropped_product_bgr)"""
        pass


class BaseVisionAnalyzer(ABC):
    @abstractmethod
    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_crop_bgr: np.ndarray | None = None,
        reference_metadata: dict[str, Any] | None = None
    ) -> EvidenceObject:
        pass

