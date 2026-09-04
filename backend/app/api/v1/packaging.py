from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.packaging import (
    PackagingVersionCreate,
    PackagingVersionResponse,
)
from backend.app.services.packaging_service import PackagingService

router = APIRouter()


@router.post("", response_model=PackagingVersionResponse, status_code=201)
async def create_packaging_version(
    data: PackagingVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"]))
):
    """
    Registers a new packaging version in DRAFT status.
    """
    return await PackagingService.create_version(db, data, creator_id=current_user.id)


@router.get("", response_model=List[PackagingVersionResponse])
@router.get("/", response_model=List[PackagingVersionResponse])
async def list_packaging_versions(
    only_active: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all registered packaging versions across products.
    """
    return await PackagingService.list_all_versions(db, only_active=only_active)


@router.get("/pack-size/{pack_size_id}", response_model=List[PackagingVersionResponse])
async def get_pack_size_versions(
    pack_size_id: str,
    only_active: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all packaging versions for a given pack size.
    """
    return await PackagingService.get_versions_by_pack_size(db, pack_size_id, only_active=only_active)


@router.put("/{version_id}/status", response_model=PackagingVersionResponse)
async def update_version_status(
    version_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"]))
):
    """
    Update version status (e.g. SUBMIT, APPROVE, ACTIVATE, DEPRECATE).
    """
    return await PackagingService.update_status(db, version_id, new_status=status, actor_id=current_user.id)
