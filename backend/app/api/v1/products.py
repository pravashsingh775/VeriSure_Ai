from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.product import (
    ProductCreate,
    ProductResponse,
    VariantCreate,
    VariantResponse,
)
from backend.app.services.product_service import ProductService

router = APIRouter()


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"]))
):
    """
    Create a new product with optional variants and pack sizes.
    """
    return await ProductService.create_product(db, data, actor_id=current_user.id)


@router.get("", response_model=List[ProductResponse])
async def list_products(
    brand_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all products, optionally filtered by brand ID.
    """
    return await ProductService.get_products(db, brand_id=brand_id)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed product specification with variants and pack sizes.
    """
    return await ProductService.get_product_by_id(db, product_id)


@router.post("/{product_id}/variants", response_model=VariantResponse, status_code=201)
async def add_variant(
    product_id: str,
    data: VariantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"]))
):
    """
    Add a new variant to an existing product.
    """
    return await ProductService.add_variant(db, product_id, data, actor_id=current_user.id)
