
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.audit import log_audit_event
from backend.app.models.product import Product, ProductPackSize, ProductVariant
from backend.app.schemas.product import (
    ProductCreate,
    ProductResponse,
    VariantCreate,
    VariantResponse,
)


class ProductService:
    @staticmethod
    async def create_product(db: AsyncSession, data: ProductCreate, actor_id: str | None = None) -> ProductResponse:
        product = Product(
            brand_id=data.brand_id,
            name=data.name,
            category=data.category,
            description=data.description,
            is_active=True
        )
        db.add(product)
        await db.flush()

        for var_data in data.variants:
            variant = ProductVariant(
                product_id=product.id,
                variant_name=var_data.variant_name,
                fat_content=var_data.fat_content,
                snf_content=var_data.snf_content,
                description=var_data.description
            )
            db.add(variant)
            await db.flush()

            for ps_data in var_data.pack_sizes:
                pack_size = ProductPackSize(
                    variant_id=variant.id,
                    pack_size=ps_data.pack_size,
                    pack_type=ps_data.pack_type,
                    net_quantity=ps_data.net_quantity
                )
                db.add(pack_size)
                await db.flush()

        await log_audit_event(
            session=db,
            action="PRODUCT_CREATED",
            resource_type="PRODUCT",
            resource_id=product.id,
            user_id=actor_id,
            changes={"name": product.name, "brand_id": product.brand_id}
        )
        await db.commit()
        return await ProductService.get_product_by_id(db, product.id)

    @staticmethod
    async def get_products(db: AsyncSession, brand_id: str | None = None) -> list[ProductResponse]:
        stmt = select(Product).options(
            selectinload(Product.variants).selectinload(ProductVariant.pack_sizes)
        )
        if brand_id:
            stmt = stmt.where(Product.brand_id == brand_id)
        stmt = stmt.order_by(Product.name.asc())

        result = await db.execute(stmt)
        products = result.scalars().all()
        return [ProductResponse.model_validate(p) for p in products]

    @staticmethod
    async def get_product_by_id(db: AsyncSession, product_id: str) -> ProductResponse:
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.variants).selectinload(ProductVariant.pack_sizes)
            )
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return ProductResponse.model_validate(product)

    @staticmethod
    async def add_variant(db: AsyncSession, product_id: str, data: VariantCreate, actor_id: str | None = None) -> VariantResponse:
        stmt = select(Product).where(Product.id == product_id)
        product = (await db.execute(stmt)).scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        variant = ProductVariant(
            product_id=product_id,
            variant_name=data.variant_name,
            fat_content=data.fat_content,
            snf_content=data.snf_content,
            description=data.description
        )
        db.add(variant)
        await db.flush()

        for ps_data in data.pack_sizes:
            ps = ProductPackSize(
                variant_id=variant.id,
                pack_size=ps_data.pack_size,
                pack_type=ps_data.pack_type,
                standard_mrp=ps_data.standard_mrp,
                net_quantity=ps_data.net_quantity
            )
            db.add(ps)
            await db.flush()

        await db.commit()
        stmt = select(ProductVariant).where(ProductVariant.id == variant.id).options(selectinload(ProductVariant.pack_sizes))
        v_loaded = (await db.execute(stmt)).scalar_one()
        return VariantResponse.model_validate(v_loaded)

