from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReferenceImageResponse(BaseModel):
    id: str
    packaging_version_id: str
    view_type: str # FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM
    image_path: str
    original_filename: str | None
    source_type: str
    source_document: str | None = None
    captured_at: datetime | None = None
    trust_level: float
    approval_status: str
    verification_status: str = "VERIFIED"
    uploaded_by: str | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    product_name: str | None = None
    variant_name: str | None = None
    pack_size: str | None = None
    version_code: str | None = None

    model_config = {"from_attributes": True}


class ReferenceFeatureResponse(BaseModel):
    id: str
    reference_image_id: str
    feature_type: str
    feature_data: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ReferenceApprovalRequest(BaseModel):
    approval_status: str = Field(pattern="^(APPROVED|REJECTED)$")
    trust_level: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = None
