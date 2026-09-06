from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    scan_id: str | None = None
    case_id: str | None = None
    verified_label: str = Field(pattern="^(GENUINE|COUNTERFEIT_SUSPICIOUS|TAMPERED|DEFECTIVE)$")
    dataset_category: str = Field(default="UNVERIFIED", pattern="^(GENUINE_REFERENCE|GENUINE_CAPTURE|VERIFIED_SUSPICIOUS|SYNTHETIC_SUSPICIOUS|UNVERIFIED|REJECTED)$")
    notes: str | None = None


class FeedbackResponse(BaseModel):
    id: str
    scan_id: str | None
    case_id: str | None
    verified_label: str
    dataset_category: str
    notes: str | None
    verified_by: str | None
    is_added_to_dataset: bool
    created_at: datetime

    model_config = {"from_attributes": True}

