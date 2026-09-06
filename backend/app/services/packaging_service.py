from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit import log_audit_event
from backend.app.models.packaging import PackagingVersion
from backend.app.models.product import ProductPackSize
from backend.app.schemas.packaging import (
    PackagingVersionCreate,
    PackagingVersionResponse,
)


class PackagingService:
    @staticmethod
    async def create_version(
        db: AsyncSession,
        data: PackagingVersionCreate,
        creator_id: str | None = None
    ) -> PackagingVersionResponse:
        # Verify pack size exists
        ps = (await db.execute(select(ProductPackSize).where(ProductPackSize.id == data.pack_size_id))).scalar_one_or_none()
        if not ps:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pack size not found")

        version = PackagingVersion(
            pack_size_id=data.pack_size_id,
            version_code=data.version_code.upper(),
            status="DRAFT",
            effective_start_date=data.effective_start_date or datetime.utcnow(),
            effective_end_date=data.effective_end_date,
            expected_barcode=data.expected_barcode,
            expected_fssai=data.expected_fssai,
            expected_mrp=data.expected_mrp,
            expected_qr_pattern=data.expected_qr_pattern,
            notes=data.notes,
            created_by=creator_id
        )
        db.add(version)
        await db.flush()

        await log_audit_event(
            session=db,
            action="PACKAGING_VERSION_CREATED",
            resource_type="PACKAGING_VERSION",
            resource_id=version.id,
            user_id=creator_id,
            changes={"version_code": version.version_code, "status": version.status}
        )
        await db.commit()
        return PackagingVersionResponse.model_validate(version)

    @staticmethod
    async def update_status(
        db: AsyncSession,
        version_id: str,
        new_status: str,
        actor_id: str | None = None
    ) -> PackagingVersionResponse:
        valid_statuses = ["DRAFT", "PENDING_REVIEW", "APPROVED", "ACTIVE", "DEPRECATED", "ARCHIVED"]
        new_status = new_status.upper()
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{new_status}'. Allowed: {valid_statuses}"
            )

        stmt = select(PackagingVersion).where(PackagingVersion.id == version_id)
        version = (await db.execute(stmt)).scalar_one_or_none()
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Packaging version not found")

        old_status = version.status
        version.status = new_status
        if new_status in ["APPROVED", "ACTIVE"]:
            version.approved_by = actor_id
            version.approved_at = datetime.utcnow()

        await log_audit_event(
            session=db,
            action="PACKAGING_VERSION_STATUS_CHANGED",
            resource_type="PACKAGING_VERSION",
            resource_id=version.id,
            user_id=actor_id,
            changes={"old_status": old_status, "new_status": new_status}
        )
        await db.commit()
        return PackagingVersionResponse.model_validate(version)

    @staticmethod
    async def get_versions_by_pack_size(
        db: AsyncSession,
        pack_size_id: str,
        only_active: bool = False
    ) -> list[PackagingVersionResponse]:
        stmt = select(PackagingVersion).where(PackagingVersion.pack_size_id == pack_size_id)
        if only_active:
            stmt = stmt.where(PackagingVersion.status == "ACTIVE")
        stmt = stmt.order_by(PackagingVersion.created_at.desc())

        result = await db.execute(stmt)
        versions = result.scalars().all()
        return [PackagingVersionResponse.model_validate(v) for v in versions]

    @staticmethod
    async def list_all_versions(
        db: AsyncSession,
        only_active: bool = False
    ) -> list[PackagingVersionResponse]:
        stmt = select(PackagingVersion)
        if only_active:
            stmt = stmt.where(PackagingVersion.status == "ACTIVE")
        stmt = stmt.order_by(PackagingVersion.created_at.desc())

        result = await db.execute(stmt)
        versions = result.scalars().all()
        return [PackagingVersionResponse.model_validate(v) for v in versions]

