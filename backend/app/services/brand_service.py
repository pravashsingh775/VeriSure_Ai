
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit import log_audit_event
from backend.app.models.brand import Brand, BrandSettings
from backend.app.schemas.brand import BrandCreate, BrandResponse


class BrandService:
    @staticmethod
    async def create_brand(db: AsyncSession, data: BrandCreate, actor_id: str | None = None) -> BrandResponse:
        stmt = select(Brand).where((Brand.name == data.name) | (Brand.code == data.code.upper()))
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A brand with this name or code already exists"
            )

        brand = Brand(
            name=data.name,
            code=data.code.upper(),
            description=data.description,
            website=data.website,
            logo_url=data.logo_url,
            is_verified=data.is_verified
        )
        db.add(brand)
        await db.flush()

        # Create default brand settings
        settings = BrandSettings(brand_id=brand.id)
        db.add(settings)
        await db.flush()

        await log_audit_event(
            session=db,
            action="BRAND_CREATED",
            resource_type="BRAND",
            resource_id=brand.id,
            user_id=actor_id,
            changes={"code": brand.code, "name": brand.name}
        )
        await db.commit()
        return BrandResponse.model_validate(brand)

    @staticmethod
    async def get_brands(db: AsyncSession) -> list[BrandResponse]:
        stmt = select(Brand).order_by(Brand.name.asc())
        result = await db.execute(stmt)
        brands = result.scalars().all()
        return [BrandResponse.model_validate(b) for b in brands]

    @staticmethod
    async def get_brand_by_id(db: AsyncSession, brand_id: str) -> BrandResponse:
        stmt = select(Brand).where(Brand.id == brand_id)
        brand = (await db.execute(stmt)).scalar_one_or_none()
        if not brand:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
        return BrandResponse.model_validate(brand)

