from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import require_roles
from backend.app.core.database import get_db
from backend.app.models.packaging import PackagingVersion
from backend.app.models.product import Product, ProductPackSize, ProductVariant
from backend.app.models.user import User
from backend.app.schemas.packaging import (
    PackagingVersionCreate,
    PackagingVersionResponse,
)
from backend.app.services.packaging_service import PackagingService

router = APIRouter()


async def _verify_brand_access(
    db: AsyncSession,
    packaging_version_id: str,
    current_user: User,
) -> None:
    """Ensure a non-platform-admin can only modify their own brand's data."""
    if current_user.is_superuser:
        return

    pv = (
        await db.execute(
            select(PackagingVersion).where(
                PackagingVersion.id == packaging_version_id
            )
        )
    ).scalar_one_or_none()

    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Packaging version not found.",
        )

    pack_size = (
        await db.execute(
            select(ProductPackSize).where(
                ProductPackSize.id == pv.pack_size_id
            )
        )
    ).scalar_one_or_none()

    if not pack_size:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced pack size not found.",
        )

    variant = (
        await db.execute(
            select(ProductVariant).where(
                ProductVariant.id == pack_size.variant_id
            )
        )
    ).scalar_one_or_none()

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced product variant not found.",
        )

    product = (
        await db.execute(
            select(Product).where(Product.id == variant.product_id)
        )
    ).scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced product not found.",
        )

    user_brand = getattr(current_user, "brand_id", None)

    if user_brand is not None and product.brand_id != user_brand:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify packaging versions for other brands.",
        )


@router.post(
    "",
    response_model=PackagingVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_packaging_version(
    data: PackagingVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"])
    ),
):
    """Register a new packaging version in DRAFT status."""
    if not current_user.is_superuser:
        pack_size = (
            await db.execute(
                select(ProductPackSize)
                .join(
                    ProductVariant,
                    ProductPackSize.variant_id == ProductVariant.id,
                )
                .join(
                    Product,
                    ProductVariant.product_id == Product.id,
                )
                .where(ProductPackSize.id == data.pack_size_id)
            )
        ).scalar_one_or_none()

        if not pack_size:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced pack size not found.",
            )

        variant = (
            await db.execute(
                select(ProductVariant).where(
                    ProductVariant.id == pack_size.variant_id
                )
            )
        ).scalar_one_or_none()

        product = (
            await db.execute(
                select(Product).where(Product.id == variant.product_id)
            )
        ).scalar_one_or_none() if variant else None

        user_brand = getattr(current_user, "brand_id", None)

        if user_brand is not None and (
            product is None or product.brand_id != user_brand
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create packaging versions for other brands.",
            )

    return await PackagingService.create_version(
        db,
        data,
        creator_id=current_user.id,
    )


@router.get("", response_model=list[PackagingVersionResponse])
@router.get("/", response_model=list[PackagingVersionResponse])
async def list_packaging_versions(
    only_active: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all registered packaging versions."""
    return await PackagingService.list_all_versions(
        db,
        only_active=only_active,
    )


@router.get(
    "/pack-size/{pack_size_id}",
    response_model=list[PackagingVersionResponse],
)
async def get_pack_size_versions(
    pack_size_id: str,
    only_active: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve packaging versions for a specific pack size."""
    return await PackagingService.get_versions_by_pack_size(
        db,
        pack_size_id,
        only_active=only_active,
    )


@router.put(
    "/{version_id}/status",
    response_model=PackagingVersionResponse,
)
async def update_version_status(
    version_id: str,
    new_status: str = Query(
        ...,
        alias="status",
        description="Target status: DRAFT, PENDING_REVIEW, APPROVED, ACTIVE, DEPRECATED, or ARCHIVED.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"])
    ),
):
    """
    Update a packaging version's lifecycle status.

    Public API parameter:
        ?status=ACTIVE

    The alias maps the public `status` parameter to the internal
    `new_status` argument expected by PackagingService.
    """
    await _verify_brand_access(
        db,
        version_id,
        current_user,
    )

    return await PackagingService.update_status(
        db,
        version_id,
        new_status=new_status,
        actor_id=current_user.id,
    )
