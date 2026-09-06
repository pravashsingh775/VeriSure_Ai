from datetime import datetime

from pydantic import BaseModel, Field


class PackagingVersionCreate(BaseModel):
    pack_size_id: str
    version_code: str = Field(min_length=1, max_length=20) # "V1", "V2"
    effective_start_date: datetime | None = None
    effective_end_date: datetime | None = None
    expected_barcode: str | None = None # EAN-13
    expected_fssai: str | None = None   # 14-digit FSSAI
    expected_mrp: float | None = None
    expected_qr_pattern: str | None = None
    notes: str | None = None


class PackagingVersionUpdate(BaseModel):
    status: str | None = None # DRAFT, PENDING_REVIEW, APPROVED, ACTIVE, DEPRECATED, ARCHIVED
    effective_start_date: datetime | None = None
    effective_end_date: datetime | None = None
    expected_barcode: str | None = None
    expected_fssai: str | None = None
    expected_mrp: float | None = None
    expected_qr_pattern: str | None = None
    notes: str | None = None


class PackagingVersionResponse(BaseModel):
    id: str
    pack_size_id: str
    version_code: str
    status: str
    effective_start_date: datetime | None
    effective_end_date: datetime | None
    expected_barcode: str | None
    expected_fssai: str | None
    expected_mrp: float | None
    expected_qr_pattern: str | None
    notes: str | None
    created_by: str | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
