from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReferenceImageResponse(BaseModel):
    id: str
    packaging_version_id: str
    view_type: str # FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM
    image_path: str
    original_filename: Optional[str]
    source_type: str
    source_document: Optional[str] = None
    captured_at: Optional[datetime] = None
    trust_level: float
    approval_status: str
    verification_status: str = "VERIFIED"
    uploaded_by: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime
    product_name: Optional[str] = None
    variant_name: Optional[str] = None
    pack_size: Optional[str] = None
    version_code: Optional[str] = None

    model_config = {"from_attributes": True}


class ReferenceFeatureResponse(BaseModel):
    id: str
    reference_image_id: str
    feature_type: str
    feature_data: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ReferenceApprovalRequest(BaseModel):
    approval_status: str = Field(pattern="^(APPROVED|REJECTED)$")
    trust_level: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    notes: Optional[str] = None
