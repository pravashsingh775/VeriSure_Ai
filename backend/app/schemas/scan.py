from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.ai.contracts import DecisionResult, EvidenceObject, QualityAssessmentResult


class ScanImageDetail(BaseModel):
    id: str
    view_type: str
    image_path: str
    crop_path: Optional[str] = None
    heatmap_path: Optional[str] = None
    quality_score: Optional[float] = None
    quality_details: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class ScanDetailResponse(BaseModel):
    id: str
    status: str
    identified_product_name: Optional[str] = None
    identified_variant_name: Optional[str] = None
    identified_pack_size: Optional[str] = None
    packaging_version_code: Optional[str] = None

    images: List[ScanImageDetail] = []
    evidences: List[EvidenceObject] = []
    decision: Optional[DecisionResult] = None
    fingerprint: Optional[Dict[str, Any]] = None
    report_url: Optional[str] = None
    suspicious_case_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanSummaryResponse(BaseModel):
    id: str
    status: str
    product_name: Optional[str] = "Unknown"
    variant_name: Optional[str] = "Unknown"
    risk_score: Optional[float] = None
    decision_state: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}

