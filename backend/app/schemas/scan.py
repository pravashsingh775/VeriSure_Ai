from datetime import datetime
from typing import Any

from pydantic import BaseModel

from backend.app.ai.contracts import DecisionResult, EvidenceObject


class ScanImageDetail(BaseModel):
    id: str
    view_type: str
    image_path: str
    crop_path: str | None = None
    heatmap_path: str | None = None
    quality_score: float | None = None
    quality_details: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ScanDetailResponse(BaseModel):
    id: str
    status: str
    identified_product_name: str | None = None
    identified_variant_name: str | None = None
    identified_pack_size: str | None = None
    packaging_version_code: str | None = None

    images: list[ScanImageDetail] = []
    evidences: list[EvidenceObject] = []
    decision: DecisionResult | None = None
    fingerprint: dict[str, Any] | None = None
    report_url: str | None = None
    suspicious_case_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanSummaryResponse(BaseModel):
    id: str
    status: str
    product_name: str | None = "Unknown"
    variant_name: str | None = "Unknown"
    risk_score: float | None = None
    decision_state: str | None = None
    confidence: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

