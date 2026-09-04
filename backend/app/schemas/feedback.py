from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    scan_id: Optional[str] = None
    case_id: Optional[str] = None
    verified_label: str = Field(pattern="^(GENUINE|COUNTERFEIT_SUSPICIOUS|TAMPERED|DEFECTIVE)$")
    dataset_category: str = Field(default="UNVERIFIED", pattern="^(GENUINE_REFERENCE|GENUINE_CAPTURE|VERIFIED_SUSPICIOUS|SYNTHETIC_SUSPICIOUS|UNVERIFIED|REJECTED)$")
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    scan_id: Optional[str]
    case_id: Optional[str]
    verified_label: str
    dataset_category: str
    notes: Optional[str]
    verified_by: Optional[str]
    is_added_to_dataset: bool
    created_at: datetime

    model_config = {"from_attributes": True}

