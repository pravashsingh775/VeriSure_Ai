from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, get_optional_user
from backend.app.core.database import get_db
from backend.app.core.storage import storage
from backend.app.models.scan import Scan
from backend.app.models.user import User
from backend.app.schemas.scan import ScanDetailResponse, ScanSummaryResponse
from backend.app.services.scan_service import ScanService

router = APIRouter()

STAFF_ROLES = {"PLATFORM_ADMIN", "BRAND_ADMIN", "BRAND_REVIEWER"}


async def _authorize_scan_access(
    scan_id: str,
    db: AsyncSession,
    current_user: User,
) -> None:
    """Ownership or staff-role check to prevent scan ID enumeration.

    Consumers may only access their own scans; staff roles (platform/brand
    triage) may access any scan for review purposes.
    """
    if current_user.is_superuser:
        return
    user_roles = {r.name for r in current_user.roles}
    if user_roles & STAFF_ROLES:
        return
    scan = (
        await db.execute(select(Scan).where(Scan.id == scan_id))
    ).scalar_one_or_none()
    if scan is None:
        # Do not reveal existence to non-owners.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    if scan.user_id is not None and scan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this scan")


@router.post("/upload", response_model=ScanDetailResponse, status_code=201)
async def upload_and_scan_product(
    file: UploadFile = File(...),
    view_type: str = Form("FRONT"),
    is_multi_angle: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    optional_user: Optional[User] = Depends(get_optional_user)
):
    """
    Submits a product photograph for multi-evidence authenticity risk assessment.
    Executes real quality assessment, product detection, reference retrieval,
    parallel evidence engines, difference heatmap, and calibrated risk calculation.
    """
    user_id = optional_user.id if optional_user else None
    return await ScanService.process_scan(
        db=db,
        file=file,
        view_type=view_type,
        user_id=user_id,
        is_multi_angle=is_multi_angle
    )


@router.post("/upload-dual", response_model=ScanDetailResponse, status_code=201)
async def upload_dual_product_scan(
    file_front: UploadFile = File(...),
    file_back: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    optional_user: Optional[User] = Depends(get_optional_user)
):
    """
    Submits both Front and Back product photographs for comprehensive 360° verification:
    - Front panel: Evaluates Logo, Typography, Layout, Colour, Shape, Texture, Front Seals.
    - Back panel: Evaluates 1D Barcode (EAN-13), QR Code, FSSAI License, Print Quality, Back Seals, Nutrition OCR.
    - Cross-side check: Ensures front variant matches back barcode identity.
    """
    user_id = optional_user.id if optional_user else None
    return await ScanService.process_dual_scan(
        db=db,
        file_front=file_front,
        file_back=file_back,
        user_id=user_id
    )


@router.get("/history/me", response_model=List[ScanSummaryResponse])
async def get_my_scan_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns scan history for the authenticated consumer with privacy isolation.
    """
    return await ScanService.list_user_scans(db, current_user.id)


@router.get("/{scan_id}", response_model=ScanDetailResponse)
async def get_scan_details(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves full verification results, including evidence breakdown,
    difference heatmap, and explainable AI narrative. Requires ownership
    or staff-level access.
    """
    await _authorize_scan_access(scan_id, db, current_user)
    return await ScanService.get_scan_detail(db, scan_id)


@router.get("/{scan_id}/report")
async def download_scan_pdf_report(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    token: Optional[str] = None,
):
    """
    Downloads the generated vector PDF report containing risk metrics,
    evidence breakdown, and academic disclaimers. Requires ownership
    or staff-level access. Supports Bearer header or ?token= query parameter.
    """
    if not current_user and token:
        try:
            from sqlalchemy.orm import selectinload
            from backend.app.core.security import decode_access_token
            payload = decode_access_token(token)
            if payload.sub:
                stmt = select(User).where(User.id == payload.sub).options(
                    selectinload(User.roles),
                    selectinload(User.brand_memberships)
                )
                res = await db.execute(stmt)
                current_user = res.scalar_one_or_none()
        except Exception:
            pass

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required to download report"
        )

    await _authorize_scan_access(scan_id, db, current_user)
    scan_detail = await ScanService.get_scan_detail(db, scan_id)
    report_rel_path = f"reports/report_{scan_id}.pdf"
    abs_path = storage.get_absolute_path(report_rel_path)

    if not abs_path.exists() and scan_detail.decision:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        from backend.app.ai.reporting.pdf_generator import VeriSurePDFGenerator
        product_metadata = {
            "brand": "AMUL",
            "product": scan_detail.identified_product_name or "Amul Dairy Product",
            "variant": scan_detail.identified_variant_name or "Standard",
            "pack_size": scan_detail.identified_pack_size or "500ml",
            "packaging_version": scan_detail.packaging_version_code or "V1",
        }
        VeriSurePDFGenerator.generate_report(
            output_pdf_path=str(abs_path),
            scan_id=scan_id,
            product_metadata=product_metadata,
            decision=scan_detail.decision,
            evidences=scan_detail.evidences,
        )

    if not abs_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF Report has not been generated for this scan."
        )

    return FileResponse(
        path=str(abs_path),
        filename=f"VeriSure_Risk_Assessment_{scan_id[:8]}.pdf",
        media_type="application/pdf"
    )
