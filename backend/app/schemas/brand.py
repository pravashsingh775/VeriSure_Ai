from datetime import datetime

from pydantic import BaseModel, Field


class BrandCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=50) # e.g. "AMUL"
    description: str | None = None
    website: str | None = None
    logo_url: str | None = None
    is_verified: bool = False


class BrandUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    website: str | None = None
    logo_url: str | None = None
    is_verified: bool | None = None


class BrandResponse(BaseModel):
    id: str
    name: str
    code: str
    description: str | None
    website: str | None
    logo_url: str | None
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
