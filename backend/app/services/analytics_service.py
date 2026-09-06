from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.brand import Brand
from backend.app.models.case import SuspiciousCase
from backend.app.models.decision import Decision
from backend.app.models.packaging import PackagingVersion
from backend.app.models.product import Product, ProductPackSize, ProductVariant
from backend.app.models.scan import Scan, ScanImage
from backend.app.schemas.analytics import (
    AdminAnalyticsResponse,
    BrandAnalyticsResponse,
    ConsumerAnalyticsResponse,
)


class AnalyticsService:
    @staticmethod
    async def get_consumer_analytics(db: AsyncSession, user_id: str) -> ConsumerAnalyticsResponse:
        stmt = select(Scan).where(Scan.user_id == user_id).options(selectinload(Scan.decision))
        scans = (await db.execute(stmt)).scalars().all()

        total = len(scans)
        genuine = sum(1 for s in scans if s.decision and s.decision.decision_state in ["LIKELY_GENUINE", "LOW_RISK"])
        suspicious = sum(1 for s in scans if s.decision and s.decision.decision_state in ["MEDIUM_RISK", "HIGH_RISK", "CRITICAL_RISK"])
        tampered = sum(1 for s in scans if s.decision and s.decision.decision_state == "TAMPERED_OR_DAMAGED")
        recent_risks = [s.decision.risk_score for s in scans[:10] if s.decision]

        return ConsumerAnalyticsResponse(
            total_scans=total,
            likely_genuine_count=genuine,
            suspicious_count=suspicious,
            tampered_count=tampered,
            recent_risk_scores=recent_risks
        )

    @staticmethod
    async def get_admin_analytics(db: AsyncSession) -> AdminAnalyticsResponse:
        # Total Scans
        total_scans = (await db.execute(select(func.count(Scan.id)))).scalar_one() or 0

        # Total Cases
        total_cases = (await db.execute(select(func.count(SuspiciousCase.id)))).scalar_one() or 0
        open_cases = (await db.execute(select(func.count(SuspiciousCase.id)).where(SuspiciousCase.status == "OPEN"))).scalar_one() or 0
        verified_cf = (await db.execute(select(func.count(SuspiciousCase.id)).where(SuspiciousCase.status == "VERIFIED_SUSPICIOUS"))).scalar_one() or 0

        # Decision distribution
        decisions = (await db.execute(select(Decision.decision_state))).scalars().all()
        decision_dist = dict(Counter(decisions))

        # Quality pass rate
        total_images = (await db.execute(select(func.count(ScanImage.id)))).scalar_one() or 1
        pass_images = (await db.execute(select(func.count(ScanImage.id)).where(ScanImage.quality_score >= 0.50))).scalar_one() or 0
        quality_pass_rate = round((pass_images / max(1, total_images)) * 100.0, 1)

        # Anomaly types
        anomaly_breakdown = {
            "Logo Mismatch": decision_dist.get("HIGH_RISK", 0) + decision_dist.get("CRITICAL_RISK", 0),
            "Heat-Seal Crimp Anomaly": decision_dist.get("TAMPERED_OR_DAMAGED", 0),
            "Barcode Contradiction": decision_dist.get("MEDIUM_RISK", 0),
            "Image Capture Insufficient": decision_dist.get("INSUFFICIENT_EVIDENCE", 0)
        }

        return AdminAnalyticsResponse(
            total_scans=total_scans,
            total_cases=total_cases,
            open_cases=open_cases,
            verified_counterfeits=verified_cf,
            quality_pass_rate_percent=quality_pass_rate,
            decision_distribution=decision_dist,
            common_anomaly_types=anomaly_breakdown
        )

    @staticmethod
    async def get_brand_analytics(db: AsyncSession, brand_id: str) -> BrandAnalyticsResponse:
        brand = (await db.execute(
            select(Brand).where((Brand.id == brand_id) | (Brand.code == brand_id.upper()))
        )).scalar_one_or_none()
        brand_name = brand.name if brand else "Amul Dairy"
        brand_code = brand.code if brand else "AMUL"
        target_brand_id = brand.id if brand else brand_id

        # Count active packaging versions
        active_versions = (
            await db.execute(
                select(func.count(PackagingVersion.id))
                .join(ProductPackSize)
                .join(ProductVariant)
                .join(Product)
                .where((Product.brand_id == target_brand_id) & (PackagingVersion.status == "ACTIVE"))
            )
        ).scalar_one() or 0

        # Total Scans for brand products
        brand_scans = (
            await db.execute(
                select(Scan)
                .join(Product, Scan.identified_product_id == Product.id)
                .where(Product.brand_id == target_brand_id)
                .options(selectinload(Scan.decision))
            )
        ).scalars().all()

        total = len(brand_scans)
        decisions = [s.decision.decision_state for s in brand_scans if s.decision]
        dist = dict(Counter(decisions))

        high_risk_count = dist.get("HIGH_RISK", 0) + dist.get("CRITICAL_RISK", 0) + dist.get("TAMPERED_OR_DAMAGED", 0)
        cf_rate = round((high_risk_count / max(1, total)) * 100.0, 1)

        return BrandAnalyticsResponse(
            brand_code=brand_code,
            brand_name=brand_name,
            total_scans=total,
            active_packaging_versions=active_versions,
            counterfeit_risk_rate_percent=cf_rate,
            risk_distribution=dist
        )

