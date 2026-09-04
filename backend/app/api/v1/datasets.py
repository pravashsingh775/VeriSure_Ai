from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    DatasetVersionCreate,
    DatasetVersionResponse,
)
from backend.app.services.dataset_service import DatasetService

router = APIRouter()


@router.post("", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    data: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN"]))
):
    """
    Create a new dataset domain container.
    """
    return await DatasetService.create_dataset(db, data, actor_id=current_user.id)


@router.get("", response_model=List[DatasetResponse])
async def list_datasets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"]))
):
    """
    List all datasets and their version snapshots.
    """
    return await DatasetService.list_datasets(db)


@router.post("/{dataset_id}/versions", response_model=DatasetVersionResponse, status_code=201)
async def create_dataset_version(
    dataset_id: str,
    data: DatasetVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN"]))
):
    """
    Creates an immutable, versioned dataset snapshot with package-isolated train/val/test splits.
    """
    return await DatasetService.create_version(db, dataset_id, data, actor_id=current_user.id)
