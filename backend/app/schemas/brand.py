from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BrandCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=50) # e.g. "AMUL"
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    is_verified: bool = False


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    is_verified: Optional[bool] = None


class BrandResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str]
    website: Optional[str]
    logo_url: Optional[str]
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
