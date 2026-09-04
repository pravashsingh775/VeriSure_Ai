from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.reference import (
    ReferenceApprovalRequest,
    ReferenceImageResponse,
)
from backend.app.services.reference_service import ReferenceService

router = APIRouter()


@router.post("/upload", response_model=ReferenceImageResponse, status_code=201)
async def upload_reference_image(
    packaging_version_id: str = Form(...),
    view_type: str = Form("FRONT"),
    source_type: str = Form("BRAND_PROVIDED"),
    trust_level: Optional[float] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"]))
):
    """
    Upload a genuine reference image for a specific packaging version and view angle.
    """
    return await ReferenceService.upload_reference_image(
        db=db,
        packaging_version_id=packaging_version_id,
        view_type=view_type,
        source_type=source_type,
        file=file,
        uploaded_by=current_user.id,
        custom_trust_level=trust_level
    )


@router.put("/{reference_id}/approval", response_model=ReferenceImageResponse)
async def approve_reference_image(
    reference_id: str,
    data: ReferenceApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"]))
):
    """
    Approve or reject a reference image and optionally adjust its trust weighting.
    """
    return await ReferenceService.approve_reference(
        db=db,
        reference_id=reference_id,
        data=data,
        actor_id=current_user.id
    )


@router.get("/version/{packaging_version_id}", response_model=List[ReferenceImageResponse])
async def list_references_for_version(
    packaging_version_id: str,
    only_approved: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    List reference images associated with a packaging version.
    """
    return await ReferenceService.get_references_by_version(
        db=db,
        packaging_version_id=packaging_version_id,
        only_approved=only_approved
    )


@router.get("", response_model=List[ReferenceImageResponse])
async def list_all_references(
    packaging_version_id: Optional[str] = None,
    only_approved: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    List all reference images with packaging version details, optionally filtered.
    """
    return await ReferenceService.get_all_references(
        db=db,
        packaging_version_id=packaging_version_id,
        only_approved=only_approved
    )

