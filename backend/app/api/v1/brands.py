
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.brand import BrandCreate, BrandResponse
from backend.app.services.brand_service import BrandService

router = APIRouter()


@router.post("", response_model=BrandResponse, status_code=201)
async def create_brand(
    data: BrandCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN"]))
):
    """
    Onboard a brand into the platform (Admin only).
    """
    return await BrandService.create_brand(db, data, actor_id=current_user.id)


@router.get("", response_model=list[BrandResponse])
async def list_brands(
    db: AsyncSession = Depends(get_db)
):
    """
    List all registered brands.
    """
    return await BrandService.get_brands(db)


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve brand profile details by ID.
    """
    return await BrandService.get_brand_by_id(db, brand_id)
