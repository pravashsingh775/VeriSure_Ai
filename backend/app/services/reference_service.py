from datetime import datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.app.core.audit import log_audit_event
from backend.app.core.storage import storage
from backend.app.models.packaging import PackagingVersion
from backend.app.models.product import ProductPackSize, ProductVariant
from backend.app.models.reference import ReferenceImage
from backend.app.schemas.reference import (
    ReferenceApprovalRequest,
    ReferenceImageResponse,
)


class ReferenceService:
    DEFAULT_TRUST_LEVELS = {
        "BRAND_PROVIDED": 1.0,
        "BRAND_APPROVED": 0.95,
        "OFFICIAL_PUBLIC_SOURCE": 0.85,
        "VERIFIED_INTERNAL_REFERENCE": 0.90,
        "OTHER": 0.50,
    }

    @staticmethod
    async def upload_reference_image(
        db: AsyncSession,
        packaging_version_id: str,
        view_type: str,
        source_type: str,
        file: UploadFile,
        uploaded_by: str | None = None,
        custom_trust_level: float | None = None,
    ) -> ReferenceImageResponse:
        # 1. Verify packaging version exists
        pv = (await db.execute(select(PackagingVersion).where(PackagingVersion.id == packaging_version_id))).scalar_one_or_none()
        if not pv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Packaging version not found")

        view_type = view_type.upper()
        if view_type not in ["FRONT", "BACK", "LEFT", "RIGHT", "TOP", "BOTTOM"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid view_type")

        source_type = source_type.upper()
        if source_type not in ReferenceService.DEFAULT_TRUST_LEVELS:
            source_type = "OTHER"

        trust = custom_trust_level if custom_trust_level is not None else ReferenceService.DEFAULT_TRUST_LEVELS[source_type]

        # 2. Save file (with upload security validation)
        contents = await file.read()
        from backend.app.core.config import settings
        from backend.app.services.scan_service import ScanService
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(contents) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
        if len(contents) > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Reference image exceeds {settings.MAX_UPLOAD_SIZE_MB} MB upload limit.")
        if not ScanService._is_decodable_image(contents):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported reference image format. Must be JPEG, PNG, or WebP.")

        rel_path, abs_path = await storage.save_bytes(
            data=contents,
            subfolder="references",
            filename=f"ref_{packaging_version_id}_{view_type.lower()}_{file.filename}",
            extension=".png"
        )

        ref_image = ReferenceImage(
            packaging_version_id=packaging_version_id,
            view_type=view_type,
            image_path=rel_path,
            original_filename=file.filename,
            source_type=source_type,
            trust_level=trust,
            approval_status="PENDING",
            uploaded_by=uploaded_by
        )
        db.add(ref_image)
        await db.flush()

        await log_audit_event(
            session=db,
            action="REFERENCE_IMAGE_UPLOADED",
            resource_type="REFERENCE_IMAGE",
            resource_id=ref_image.id,
            user_id=uploaded_by,
            changes={"view_type": view_type, "trust_level": trust, "source": source_type}
        )
        await db.commit()
        return ReferenceImageResponse.model_validate(ref_image)

    @staticmethod
    async def approve_reference(
        db: AsyncSession,
        reference_id: str,
        data: ReferenceApprovalRequest,
        actor_id: str | None = None
    ) -> ReferenceImageResponse:
        stmt = select(ReferenceImage).where(ReferenceImage.id == reference_id)
        ref = (await db.execute(stmt)).scalar_one_or_none()
        if not ref:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference image not found")

        ref.approval_status = data.approval_status
        if data.trust_level is not None:
            ref.trust_level = data.trust_level
        ref.approved_by = actor_id
        ref.approved_at = datetime.utcnow()

        await log_audit_event(
            session=db,
            action=f"REFERENCE_IMAGE_{data.approval_status}",
            resource_type="REFERENCE_IMAGE",
            resource_id=ref.id,
            user_id=actor_id,
            changes={"approval_status": ref.approval_status, "trust_level": ref.trust_level}
        )
        await db.commit()
        return ReferenceImageResponse.model_validate(ref)

    @staticmethod
    def _enrich_reference_response(ref: ReferenceImage) -> ReferenceImageResponse:
        pv = getattr(ref, "packaging_version", None)
        ps = getattr(pv, "pack_size", None) if pv else None
        var = getattr(ps, "variant", None) if ps else None
        prod = getattr(var, "product", None) if var else None

        resp = ReferenceImageResponse.model_validate(ref)
        if prod:
            resp.product_name = prod.name
        if var:
            resp.variant_name = var.variant_name
        if ps:
            resp.pack_size = ps.pack_size
        if pv:
            resp.version_code = pv.version_code
        return resp

    @staticmethod
    async def get_references_by_version(
        db: AsyncSession,
        packaging_version_id: str,
        only_approved: bool = False
    ) -> list[ReferenceImageResponse]:
        stmt = (
            select(ReferenceImage)
            .where(ReferenceImage.packaging_version_id == packaging_version_id)
            .options(
                joinedload(ReferenceImage.packaging_version)
                .joinedload(PackagingVersion.pack_size)
                .joinedload(ProductPackSize.variant)
                .joinedload(ProductVariant.product)
            )
        )
        if only_approved:
            stmt = stmt.where(ReferenceImage.approval_status == "APPROVED")
        stmt = stmt.order_by(ReferenceImage.created_at.asc())

        result = await db.execute(stmt)
        refs = result.scalars().all()
        return [ReferenceService._enrich_reference_response(r) for r in refs]

    @staticmethod
    async def get_all_references(
        db: AsyncSession,
        packaging_version_id: str | None = None,
        only_approved: bool = False
    ) -> list[ReferenceImageResponse]:
        stmt = (
            select(ReferenceImage)
            .options(
                joinedload(ReferenceImage.packaging_version)
                .joinedload(PackagingVersion.pack_size)
                .joinedload(ProductPackSize.variant)
                .joinedload(ProductVariant.product)
            )
        )
        if packaging_version_id:
            stmt = stmt.where(ReferenceImage.packaging_version_id == packaging_version_id)
        if only_approved:
            stmt = stmt.where(ReferenceImage.approval_status == "APPROVED")
        stmt = stmt.order_by(ReferenceImage.created_at.asc())

        result = await db.execute(stmt)
        refs = result.scalars().all()
        return [ReferenceService._enrich_reference_response(r) for r in refs]

