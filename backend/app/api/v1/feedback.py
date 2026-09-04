from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.feedback import FeedbackCreate, FeedbackResponse
from backend.app.services.feedback_service import FeedbackService

router = APIRouter()


@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_verified_feedback(
    data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN", "BRAND_REVIEWER"]))
):
    """
    Submits expert verified ground-truth feedback from a reviewed scan or suspicious case.
    Feeds into the human-in-the-loop curated learning dataset.
    """
    return await FeedbackService.record_feedback(db, data, verified_by_id=current_user.id)


@router.get("", response_model=List[FeedbackResponse])
async def list_feedback_samples(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"]))
):
    """
    List curated feedback samples.
    """
    return await FeedbackService.list_feedback(db)
