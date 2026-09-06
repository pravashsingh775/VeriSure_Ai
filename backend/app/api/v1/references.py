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
    if not current_user.is_superuser:
        from fastapi import HTTPException, status
        from sqlalchemy import select
        from backend.app.models.packaging import PackagingVersion
        from backend.app.models.product import Product, ProductPackSize, ProductVariant
        pv = (await db.execute(select(PackagingVersion).where(PackagingVersion.id == packaging_version_id))).scalar_one_or_none()
        if not pv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Packaging version not found")
        pack_size = (await db.execute(select(ProductPackSize).where(ProductPackSize.id == pv.pack_size_id))).scalar_one_or_none()
        if pack_size:
            variant = (await db.execute(select(ProductVariant).where(ProductVariant.id == pack_size.variant_id))).scalar_one_or_none()
            if variant:
                product = (await db.execute(select(Product).where(Product.id == variant.product_id))).scalar_one_or_none()
                user_brand = getattr(current_user, "brand_id", None)
                if user_brand and product and product.brand_id != user_brand:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot upload reference images for other brands.")

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
    if not current_user.is_superuser:
        from fastapi import HTTPException, status
        from sqlalchemy import select
        from backend.app.models.packaging import PackagingVersion
        from backend.app.models.product import Product, ProductPackSize, ProductVariant
        from backend.app.models.reference import ReferenceImage
        ref = (await db.execute(select(ReferenceImage).where(ReferenceImage.id == reference_id))).scalar_one_or_none()
        if not ref:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference image not found.")
        pv = (await db.execute(select(PackagingVersion).where(PackagingVersion.id == ref.packaging_version_id))).scalar_one_or_none()
        if pv:
            pack_size = (await db.execute(select(ProductPackSize).where(ProductPackSize.id == pv.pack_size_id))).scalar_one_or_none()
            if pack_size:
                variant = (await db.execute(select(ProductVariant).where(ProductVariant.id == pack_size.variant_id))).scalar_one_or_none()
                if variant:
                    product = (await db.execute(select(Product).where(Product.id == variant.product_id))).scalar_one_or_none()
                    user_brand = getattr(current_user, "brand_id", None)
                    if user_brand and product and product.brand_id != user_brand:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot approve reference images for other brands.")

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

