from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.analytics import (
    AdminAnalyticsResponse,
    BrandAnalyticsResponse,
    ConsumerAnalyticsResponse,
)
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/consumer", response_model=ConsumerAnalyticsResponse)
async def get_consumer_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Consumer dashboard metrics for the authenticated user.
    """
    return await AnalyticsService.get_consumer_analytics(db, current_user.id)


@router.get("/admin", response_model=AdminAnalyticsResponse)
async def get_admin_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN", "BRAND_REVIEWER"]))
):
    """
    Platform-wide operational analytics, quality pass rates, and risk distribution.
    """
    return await AnalyticsService.get_admin_analytics(db)


@router.get("/brand/{brand_id}", response_model=BrandAnalyticsResponse)
async def get_brand_analytics(
    brand_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN", "BRAND_REVIEWER"]))
):
    """
    Brand-specific telemetry, active packaging versions, and counterfeit anomaly rate.
    """
    return await AnalyticsService.get_brand_analytics(db, brand_id)
