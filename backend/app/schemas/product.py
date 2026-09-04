from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PackSizeCreate(BaseModel):
    pack_size: str = Field(min_length=1, max_length=50) # "500ml", "1L"
    pack_type: str = "POUCH" # POUCH, TETRA_PACK, BOTTLE, CUP
    net_quantity: Optional[str] = None


class PackSizeResponse(BaseModel):
    id: str
    variant_id: str
    pack_size: str
    pack_type: str
    net_quantity: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VariantCreate(BaseModel):
    variant_name: str = Field(min_length=1, max_length=100) # e.g. "Taaza", "Gold"
    fat_content: Optional[str] = None
    snf_content: Optional[str] = None
    description: Optional[str] = None
    pack_sizes: List[PackSizeCreate] = []


class VariantResponse(BaseModel):
    id: str
    product_id: str
    variant_name: str
    fat_content: Optional[str]
    snf_content: Optional[str]
    description: Optional[str]
    pack_sizes: List[PackSizeResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    brand_id: str
    name: str = Field(min_length=2, max_length=150)
    category: str = "MILK"
    description: Optional[str] = None
    variants: List[VariantCreate] = []


class ProductResponse(BaseModel):
    id: str
    brand_id: str
    name: str
    category: str
    description: Optional[str]
    is_active: bool
    variants: List[VariantResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
