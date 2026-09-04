from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PackagingVersionCreate(BaseModel):
    pack_size_id: str
    version_code: str = Field(min_length=1, max_length=20) # "V1", "V2"
    effective_start_date: Optional[datetime] = None
    effective_end_date: Optional[datetime] = None
    expected_barcode: Optional[str] = None # EAN-13
    expected_fssai: Optional[str] = None   # 14-digit FSSAI
    expected_mrp: Optional[float] = None
    expected_qr_pattern: Optional[str] = None
    notes: Optional[str] = None


class PackagingVersionUpdate(BaseModel):
    status: Optional[str] = None # DRAFT, PENDING_REVIEW, APPROVED, ACTIVE, DEPRECATED, ARCHIVED
    effective_start_date: Optional[datetime] = None
    effective_end_date: Optional[datetime] = None
    expected_barcode: Optional[str] = None
    expected_fssai: Optional[str] = None
    expected_mrp: Optional[float] = None
    expected_qr_pattern: Optional[str] = None
    notes: Optional[str] = None


class PackagingVersionResponse(BaseModel):
    id: str
    pack_size_id: str
    version_code: str
    status: str
    effective_start_date: Optional[datetime]
    effective_end_date: Optional[datetime]
    expected_barcode: Optional[str]
    expected_fssai: Optional[str]
    expected_mrp: Optional[float]
    expected_qr_pattern: Optional[str]
    notes: Optional[str]
    created_by: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
