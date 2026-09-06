import asyncio
from datetime import datetime
from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal, init_db
from backend.app.core.security import get_password_hash
from backend.app.models import (
    Brand,
    BrandSettings,
    BrandUser,
    PackagingVersion,
    Product,
    ProductPackSize,
    ProductVariant,
    Role,
    User,
    UserRole,
)


async def seed_database():
    print("Initializing database tables...")
    await init_db()

    async with AsyncSessionLocal() as session:
        print("Seeding roles...")
        roles_data = [
            ("CONSUMER", "End-user consumer scanning products"),
            ("PLATFORM_ADMIN", "Full platform administration privileges"),
            ("BRAND_ADMIN", "Brand partner manager for catalog and references"),
            ("BRAND_REVIEWER", "Brand reviewer inspecting suspicious triage cases"),
        ]
        role_objs = {}
        for r_name, r_desc in roles_data:
            existing = (await session.execute(select(Role).where(Role.name == r_name))).scalar_one_or_none()
            if not existing:
                role = Role(name=r_name, description=r_desc)
                session.add(role)
                await session.flush()
                role_objs[r_name] = role
            else:
                role_objs[r_name] = existing

        print("Seeding Amul Brand...")
        amul_brand = (await session.execute(select(Brand).where(Brand.code == "AMUL"))).scalar_one_or_none()
        if not amul_brand:
            amul_brand = Brand(
                name="Amul Dairy",
                code="AMUL",
                description="Gujarat Cooperative Milk Marketing Federation Ltd (GCMMF) - The Taste of India",
                website="https://amul.com",
                logo_url="https://amul.com/images/amul_logo.png",
                is_verified=True
            )
            session.add(amul_brand)
            await session.flush()

            settings = BrandSettings(
                brand_id=amul_brand.id,
                auto_triage_threshold=65.0,
                allowed_domains="amul.com,gcmmf.com",
                notification_email="brand-security@amul.coop"
            )
            session.add(settings)
            await session.flush()

        print("Seeding Users & Brand Memberships (Normalized RBAC)...")
        users_data = [
            ("admin@verisure.ai", "Platform Admin", "Admin@12345", "PLATFORM_ADMIN", None, True),
            ("amul_admin@verisure.ai", "Amul Brand Lead", "Amul@12345", "BRAND_ADMIN", amul_brand.id, False),
            ("amul_reviewer@verisure.ai", "Amul Triage Reviewer", "Reviewer@12345", "BRAND_REVIEWER", amul_brand.id, False),
            ("consumer@verisure.ai", "Jane Consumer", "Consumer@12345", "CONSUMER", None, False),
        ]
        for email, name, pwd, role_name, b_id, is_super in users_data:
            existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if not existing:
                user = User(
                    email=email,
                    hashed_password=get_password_hash(pwd),
                    full_name=name,
                    is_active=True,
                    is_superuser=is_super
                )
                session.add(user)
                await session.flush()
                user_role = UserRole(user_id=user.id, role_id=role_objs[role_name].id)
                session.add(user_role)
                await session.flush()
            else:
                user = existing

            # Brand membership in brand_users
            if b_id:
                existing_bu = (await session.execute(
                    select(BrandUser).where((BrandUser.brand_id == b_id) & (BrandUser.user_id == user.id))
                )).scalar_one_or_none()
                if not existing_bu:
                    b_role = "ADMIN" if role_name == "BRAND_ADMIN" else "MEMBER"
                    b_user = BrandUser(brand_id=b_id, user_id=user.id, role=b_role)
                    session.add(b_user)
                    await session.flush()

        print("Seeding Locked Product Scope: Amul Taaza, Amul Gold, Amul Shakti (Category: MILK)...")
        catalog = [
            {
                "name": "Amul Taaza",
                "category": "MILK",
                "desc": "Pasteurised homogenised toned milk, double pasteurised for superior nutrition.",
                "variants": [
                    {
                        "name": "Toned Milk",
                        "fat": "3.5% min",
                        "snf": "8.5% min",
                        "pack_sizes": [
                            {
                                "size": "500ml",
                                "type": "POUCH",
                                "mrp": 27.0,
                                "qty": "500 ml",
                                "barcode": "8901262010053",
                                "fssai": "10012021000071"
                            },
                            {
                                "size": "1L",
                                "type": "POUCH",
                                "mrp": 54.0,
                                "qty": "1000 ml",
                                "barcode": "8901262260091",
                                "fssai": "10012021000071"
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Amul Gold",
                "category": "MILK",
                "desc": "Rich, creamy, full-cream pasteurised standardized milk ideal for direct consumption and sweets.",
                "variants": [
                    {
                        "name": "Full Cream Milk",
                        "fat": "6.0% min",
                        "snf": "9.0% min",
                        "pack_sizes": [
                            {
                                "size": "500ml",
                                "type": "POUCH",
                                "mrp": 33.0,
                                "qty": "500 ml",
                                "barcode": "8901262010015",
                                "fssai": "10012021000071"
                            },
                            {
                                "size": "1L",
                                "type": "POUCH",
                                "mrp": 66.0,
                                "qty": "1000 ml",
                                "barcode": "8901262260114",
                                "fssai": "10012021000071"
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Amul Shakti",
                "category": "MILK",
                "desc": "Pasteurised standardised milk balancing energy and nutrition for active families.",
                "variants": [
                    {
                        "name": "Standardised Milk",
                        "fat": "4.5% min",
                        "snf": "8.5% min",
                        "pack_sizes": [
                            {
                                "size": "500ml",
                                "type": "POUCH",
                                "mrp": 30.0,
                                "qty": "500 ml",
                                "barcode": "8901262260138",
                                "fssai": "10012021000071"
                            }
                        ]
                    }
                ]
            }
        ]

        for p_data in catalog:
            product = (await session.execute(
                select(Product).where((Product.name == p_data["name"]) & (Product.brand_id == amul_brand.id))
            )).scalar_one_or_none()

            if not product:
                product = Product(
                    brand_id=amul_brand.id,
                    name=p_data["name"],
                    category=p_data["category"],
                    description=p_data["desc"],
                    is_active=True
                )
                session.add(product)
                await session.flush()
            else:
                # Update category to MILK if it was previously DAIRY
                product.category = p_data["category"]
                await session.flush()

            for v_data in p_data["variants"]:
                variant = (await session.execute(
                    select(ProductVariant).where((ProductVariant.product_id == product.id) & (ProductVariant.variant_name == v_data["name"]))
                )).scalar_one_or_none()

                if not variant:
                    variant = ProductVariant(
                        product_id=product.id,
                        variant_name=v_data["name"],
                        fat_content=v_data["fat"],
                        snf_content=v_data["snf"],
                        description=f"{p_data['name']} {v_data['name']}"
                    )
                    session.add(variant)
                    await session.flush()

                for ps_data in v_data["pack_sizes"]:
                    pack_size = (await session.execute(
                        select(ProductPackSize).where(
                            (ProductPackSize.variant_id == variant.id) &
                            (ProductPackSize.pack_size == ps_data["size"]) &
                            (ProductPackSize.pack_type == ps_data["type"])
                        )
                    )).scalar_one_or_none()

                    if not pack_size:
                        pack_size = ProductPackSize(
                            variant_id=variant.id,
                            pack_size=ps_data["size"],
                            pack_type=ps_data["type"],
                            net_quantity=ps_data["qty"]
                        )
                        session.add(pack_size)
                        await session.flush()

                    # Packaging version V1 with versioned expected_mrp
                    version = (await session.execute(
                        select(PackagingVersion).where(
                            (PackagingVersion.pack_size_id == pack_size.id) &
                            (PackagingVersion.version_code == "V1")
                        )
                    )).scalar_one_or_none()

                    if not version:
                        version = PackagingVersion(
                            pack_size_id=pack_size.id,
                            version_code="V1",
                            status="ACTIVE",
                            effective_start_date=datetime(2023, 1, 1),
                            expected_barcode=ps_data["barcode"],
                            expected_fssai=ps_data["fssai"],
                            expected_mrp=ps_data["mrp"],
                            notes="Standard Production Packaging Specification"
                        )
                        session.add(version)
                        await session.flush()
                    else:
                        version.expected_mrp = ps_data["mrp"]
                        version.expected_barcode = ps_data["barcode"]
                        await session.flush()

        await session.commit()
        print("Database successfully seeded with locked Amul milk catalog (Taaza, Gold, Shakti)!")


if __name__ == "__main__":
    asyncio.run(seed_database())
