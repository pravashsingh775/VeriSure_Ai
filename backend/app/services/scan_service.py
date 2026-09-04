import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.ai.contracts import DecisionResult, DecisionState, EvidenceObject, EvidenceType, RegionBox
from backend.app.ai.orchestrator import orchestrator
from backend.app.core.audit import log_audit_event
from backend.app.core.config import settings
from backend.app.core.storage import storage
from backend.app.models.case import SuspiciousCase
from backend.app.models.decision import Decision
from backend.app.models.evidence import Evidence, PackagingFingerprintRecord
from backend.app.models.product import Product, ProductPackSize, ProductVariant
from backend.app.models.report import ReportRecord
from backend.app.models.scan import Scan, ScanImage
from backend.app.schemas.scan import ScanDetailResponse, ScanImageDetail, ScanSummaryResponse


class ScanService:
    MAGIC_SIGNATURES = (
        b"\xff\xd8\xff",          # JPEG
        b"\x89PNG\r\n\x1a\n",    # PNG
        b"RIFF",                   # WebP (RIFF container, WEBP at offset 8)
    )

    @staticmethod
    def _is_decodable_image(data: bytes) -> bool:
        """Validate real image format via magic bytes, not client headers."""
        if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
            return True
        return any(data.startswith(sig) for sig in ScanService.MAGIC_SIGNATURES)

    @staticmethod
    async def process_scan(
        db: AsyncSession,
        file: UploadFile,
        view_type: str = "FRONT",
        user_id: Optional[str] = None,
        is_multi_angle: bool = False
    ) -> ScanDetailResponse:
        # 1. Create Scan record
        scan = Scan(
            user_id=user_id,
            status="ANALYZING",
            total_images=1,
            is_multi_angle=is_multi_angle
        )
        db.add(scan)
        await db.flush()

        # 2. Save raw upload to storage (with validation first)
        raw_bytes = await file.read()

        # --- Upload validation: enforce configured size cap and real image format ---
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(raw_bytes) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
        if len(raw_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB upload limit.",
            )
        # Sniff the magic bytes instead of trusting the client Content-Type header.
        if not ScanService._is_decodable_image(raw_bytes):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported file type: please upload a JPEG, PNG, or WebP image.",
            )

        rel_path, abs_path = await storage.save_bytes(
            data=raw_bytes,
            subfolder="raw_scans",
            filename=f"scan_{scan.id}_{view_type.lower()}_{file.filename}",
            extension=".png"
        )

        # 3. Read image with OpenCV
        img_bgr = cv2.imread(abs_path)
        if img_bgr is None or img_bgr.size == 0:
            scan.status = "FAILED"
            scan.error_code = "VERISURE-IMG-001"
            scan.error_message = "Unable to decode image file format."
            await db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=scan.error_message)
        # Guard against decompression bombs (pixel-count cap; ~80 MP).
        if img_bgr.shape[0] * img_bgr.shape[1] > 80_000_000:
            scan.status = "FAILED"
            scan.error_code = "VERISURE-IMG-002"
            scan.error_message = "Image dimensions exceed the supported maximum."
            await db.commit()
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=scan.error_message)

        # 4. Execute Full AI Orchestration Pipeline
        pipeline_output = await orchestrator.execute_pipeline(
            db=db,
            scan_id=scan.id,
            image_bgr=img_bgr,
            view_type=view_type
        )

        quality_res = pipeline_output["quality"]
        det_box = pipeline_output["detection"]
        decision_res: DecisionResult = pipeline_output["decision"]
        evidences: List[EvidenceObject] = pipeline_output["evidences"]
        best_candidate = pipeline_output.get("identified_product")

        # 5. Persist Scan Image
        scan_image = ScanImage(
            scan_id=scan.id,
            view_type=view_type,
            image_path=rel_path,
            original_filename=file.filename,
            quality_score=quality_res.overall_quality,
            quality_details=quality_res.model_dump(),
            detected_bbox=list(det_box.bbox),
            crop_path=pipeline_output["crop_path"],
            heatmap_path=pipeline_output["heatmap_path"]
        )
        db.add(scan_image)

        # 6. Persist Evidences
        for ev in evidences:
            ev_record = Evidence(
                scan_id=scan.id,
                evidence_type=ev.type.value,
                score=ev.score,
                confidence=ev.confidence,
                availability=ev.availability,
                quality=ev.quality,
                source=ev.source,
                reference_id=best_candidate.get("reference_image_id") if best_candidate else None,
                model_version=ev.model_version,
                features=ev.features,
                regions=[r.model_dump() for r in ev.regions],
                explanation=ev.explanation,
                warnings=ev.warnings
            )
            db.add(ev_record)

        # 7. Persist Decision
        decision_record = Decision(
            scan_id=scan.id,
            decision_state=decision_res.state.value,
            risk_score=decision_res.risk_score,
            confidence=decision_res.confidence,
            uncertainty=decision_res.uncertainty,
            evidence_coverage=decision_res.evidence_coverage,
            recommendation=decision_res.recommendation,
            reason_codes=decision_res.reason_codes,
            explanation_summary=decision_res.explanation_summary,
            contradictions=decision_res.contradictions
        )
        db.add(decision_record)

        # 8. Persist Fingerprint
        if fingerprint := pipeline_output.get("fingerprint"):
            fp_record = PackagingFingerprintRecord(
                scan_id=scan.id,
                fingerprint_json=fingerprint.model_dump()
            )
            db.add(fp_record)

        # 9. Persist Report Record
        if report_rel := pipeline_output.get("report_path"):
            report_abs = storage.get_absolute_path(report_rel)
            file_size = os.path.getsize(report_abs) if report_abs.exists() else 0
            pdf_sha = None
            if report_abs.exists():
                import hashlib
                with open(report_abs, "rb") as f:
                    pdf_sha = hashlib.sha256(f.read()).hexdigest()
            rep_record = ReportRecord(
                scan_id=scan.id,
                pdf_path=report_rel,
                pdf_sha256=pdf_sha,
                file_size_bytes=file_size,
                generated_at=datetime.utcnow()
            )
            db.add(rep_record)

        # 10. Update Scan Metadata
        scan.status = "REPORT_READY"
        scan.completed_at = datetime.utcnow()
        if best_candidate:
            scan.identified_product_id = best_candidate.get("product_id")
            scan.identified_packaging_version_id = best_candidate.get("packaging_version_id")
            scan.matched_reference_id = best_candidate.get("reference_image_id")

        # 11. Auto-Triage Suspicious Case if high risk or tampered
        suspicious_case_id = None
        if decision_res.risk_score >= 60.0 or decision_res.state in [
            DecisionState.CRITICAL_RISK,
            DecisionState.HIGH_RISK,
            DecisionState.TAMPERED_OR_DAMAGED
        ]:
            # Get Amul brand id or candidate brand
            brand_id = (await db.execute(select(Product.brand_id).where(Product.id == scan.identified_product_id))).scalar_one_or_none() if scan.identified_product_id else None
            if not brand_id:
                # Default to Amul
                from backend.app.models.brand import Brand
                brand_id = (await db.execute(select(Brand.id).where(Brand.code == "AMUL"))).scalar_one_or_none()

            if brand_id:
                case = SuspiciousCase(
                    scan_id=scan.id,
                    brand_id=brand_id,
                    case_number=f"CASE-{datetime.utcnow().strftime('%Y%m%d')}-{scan.id[:8].upper()}",
                    status="OPEN",
                    priority="HIGH" if decision_res.risk_score >= 75.0 else "MEDIUM",
                    notes=f"Auto-generated triage case. Risk Score: {decision_res.risk_score}/100. State: {decision_res.state.value}."
                )
                db.add(case)
                await db.flush()
                suspicious_case_id = case.id

        await log_audit_event(
            session=db,
            action="SCAN_PROCESSED",
            resource_type="SCAN",
            resource_id=scan.id,
            user_id=user_id,
            changes={
                "risk_score": decision_res.risk_score,
                "state": decision_res.state.value,
                "product": best_candidate.get("product_name") if best_candidate else "Unknown"
            }
        )
        await db.commit()

        # Construct and return full response
        return await ScanService.get_scan_detail(db, scan.id)

    @staticmethod
    async def get_scan_detail(db: AsyncSession, scan_id: str) -> ScanDetailResponse:
        stmt = (
            select(Scan)
            .where(Scan.id == scan_id)
            .options(
                selectinload(Scan.images),
                selectinload(Scan.evidences),
                selectinload(Scan.decision),
                selectinload(Scan.fingerprint),
                selectinload(Scan.report),
                selectinload(Scan.suspicious_case)
            )
        )
        scan = (await db.execute(stmt)).scalar_one_or_none()
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

        # Resolve Product & Version details
        product_name = None
        variant_name = None
        pack_size = None
        version_code = None

        if scan.identified_product_id:
            p = (await db.execute(select(Product).where(Product.id == scan.identified_product_id))).scalar_one_or_none()
            if p:
                product_name = p.name

        if scan.identified_packaging_version_id:
            from backend.app.models.packaging import PackagingVersion
            pv = (await db.execute(select(PackagingVersion).where(PackagingVersion.id == scan.identified_packaging_version_id).options(selectinload(PackagingVersion.pack_size).selectinload(ProductPackSize.variant)))).scalar_one_or_none()
            if pv:
                version_code = pv.version_code
                if pv.pack_size:
                    pack_size = pv.pack_size.pack_size
                    if pv.pack_size.variant:
                        variant_name = pv.pack_size.variant.variant_name

        image_details = [
            ScanImageDetail(
                id=img.id,
                view_type=img.view_type,
                image_path=img.image_path,
                crop_path=img.crop_path,
                heatmap_path=img.heatmap_path,
                quality_score=img.quality_score,
                quality_details=img.quality_details
            )
            for img in scan.images
        ]

        evidence_objects = [
            EvidenceObject(
                id=ev.id,
                type=EvidenceType(ev.evidence_type),
                score=ev.score,
                confidence=ev.confidence,
                availability=ev.availability,
                quality=ev.quality,
                source=ev.source,
                reference_id=ev.reference_id,
                model_version=ev.model_version,
                features=ev.features or {},
                regions=[RegionBox(**r) for r in (ev.regions or [])],
                explanation=ev.explanation,
                warnings=ev.warnings or [],
                created_at=ev.created_at
            )
            for ev in scan.evidences
        ]

        decision_obj = None
        if d := scan.decision:
            decision_obj = DecisionResult(
                state=DecisionState(d.decision_state),
                risk_score=d.risk_score,
                confidence=d.confidence,
                uncertainty=d.uncertainty,
                evidence_coverage=d.evidence_coverage,
                recommendation=d.recommendation,
                reason_codes=d.reason_codes or [],
                explanation_summary=d.explanation_summary,
                contradictions=d.contradictions or [],
                suspicious_regions=[]
            )

        report_url = f"/api/v1/scans/{scan.id}/report" if scan.report else None

        return ScanDetailResponse(
            id=scan.id,
            status=scan.status,
            identified_product_name=product_name,
            identified_variant_name=variant_name,
            identified_pack_size=pack_size,
            packaging_version_code=version_code,
            images=image_details,
            evidences=evidence_objects,
            decision=decision_obj,
            fingerprint=scan.fingerprint.fingerprint_json if scan.fingerprint else None,
            report_url=report_url,
            suspicious_case_id=scan.suspicious_case.id if scan.suspicious_case else None,
            created_at=scan.created_at
        )

    @staticmethod
    async def list_user_scans(db: AsyncSession, user_id: str) -> List[ScanSummaryResponse]:
        stmt = (
            select(Scan)
            .where(Scan.user_id == user_id)
            .options(
                selectinload(Scan.decision)
            )
            .order_by(Scan.created_at.desc())
        )
        result = await db.execute(stmt)
        scans = result.scalars().all()

        summaries: List[ScanSummaryResponse] = []
        for s in scans:
            p_name = "Unknown"
            if s.identified_product_id:
                p = (await db.execute(select(Product.name).where(Product.id == s.identified_product_id))).scalar_one_or_none()
                if p:
                    p_name = p

            summaries.append(ScanSummaryResponse(
                id=s.id,
                status=s.status,
                product_name=p_name,
                risk_score=s.decision.risk_score if s.decision else None,
                decision_state=s.decision.decision_state if s.decision else None,
                confidence=s.decision.confidence if s.decision else None,
                created_at=s.created_at
            ))

        return summaries

