from datetime import datetime

from pydantic import BaseModel, Field


class PackSizeCreate(BaseModel):
    pack_size: str = Field(min_length=1, max_length=50) # "500ml", "1L"
    pack_type: str = "POUCH" # POUCH, TETRA_PACK, BOTTLE, CUP
    net_quantity: str | None = None


class PackSizeResponse(BaseModel):
    id: str
    variant_id: str
    pack_size: str
    pack_type: str
    net_quantity: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VariantCreate(BaseModel):
    variant_name: str = Field(min_length=1, max_length=100) # e.g. "Taaza", "Gold"
    fat_content: str | None = None
    snf_content: str | None = None
    description: str | None = None
    pack_sizes: list[PackSizeCreate] = []


class VariantResponse(BaseModel):
    id: str
    product_id: str
    variant_name: str
    fat_content: str | None
    snf_content: str | None
    description: str | None
    pack_sizes: list[PackSizeResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    brand_id: str
    name: str = Field(min_length=2, max_length=150)
    category: str = "MILK"
    description: str | None = None
    variants: list[VariantCreate] = []


class ProductResponse(BaseModel):
    id: str
    brand_id: str
    name: str
    category: str
    description: str | None
    is_active: bool
    variants: list[VariantResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
