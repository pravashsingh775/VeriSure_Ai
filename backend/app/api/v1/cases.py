from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.case import CaseResponse, CaseReviewCreate
from backend.app.services.case_service import CaseService

router = APIRouter()


@router.get("", response_model=List[CaseResponse])
async def list_suspicious_cases(
    brand_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN", "BRAND_REVIEWER"]))
):
    """
    List suspicious verification cases pending triage and human review.
    """
    # Scope brand users to their own brand
    if not current_user.is_superuser and current_user.brand_id:
        brand_id = current_user.brand_id

    return await CaseService.list_cases(db, brand_id=brand_id, status_filter=status)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case_details(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN", "BRAND_REVIEWER"]))
):
    """
    Retrieve suspicious case details, audit history, and associated scan evidence.
    """
    return await CaseService.get_case_by_id(db, case_id)


@router.post("/{case_id}/review", response_model=CaseResponse)
async def submit_case_review(
    case_id: str,
    data: CaseReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN", "BRAND_REVIEWER"]))
):
    """
    Records an expert human review transition (e.g. VERIFIED_SUSPICIOUS, VERIFIED_GENUINE, REJECTED).
    """
    return await CaseService.add_review(
        db=db,
        case_id=case_id,
        data=data,
        reviewer_id=current_user.id
    )
