from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CaseReviewResponse(BaseModel):
    id: str
    reviewer_id: str
    previous_status: str
    new_status: str
    comments: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseReviewCreate(BaseModel):
    new_status: str = Field(pattern="^(UNDER_REVIEW|NEEDS_MORE_EVIDENCE|VERIFIED_GENUINE|VERIFIED_SUSPICIOUS|REJECTED|CLOSED)$")
    comments: str = Field(min_length=3)


class CaseResponse(BaseModel):
    id: str
    scan_id: str
    brand_id: str
    case_number: str
    status: str
    priority: str
    assigned_to: Optional[str]
    notes: Optional[str]
    reviews: List[CaseReviewResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

