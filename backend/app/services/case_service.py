
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.audit import log_audit_event
from backend.app.models.case import CaseReview, SuspiciousCase
from backend.app.schemas.case import CaseResponse, CaseReviewCreate, CaseReviewResponse


class CaseService:
    @staticmethod
    async def list_cases(
        db: AsyncSession,
        brand_id: str | None = None,
        status_filter: str | None = None
    ) -> list[CaseResponse]:
        stmt = select(SuspiciousCase).options(selectinload(SuspiciousCase.reviews))
        if brand_id:
            stmt = stmt.where(SuspiciousCase.brand_id == brand_id)
        if status_filter:
            stmt = stmt.where(SuspiciousCase.status == status_filter.upper())
        stmt = stmt.order_by(SuspiciousCase.created_at.desc())

        result = await db.execute(stmt)
        cases = result.scalars().all()
        return [
            CaseResponse(
                id=c.id,
                scan_id=c.scan_id,
                brand_id=c.brand_id,
                case_number=c.case_number,
                status=c.status,
                priority=c.priority,
                assigned_to=c.assigned_to,
                notes=c.notes,
                reviews=[CaseReviewResponse.model_validate(r) for r in c.reviews],
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in cases
        ]

    @staticmethod
    async def get_case_by_id(db: AsyncSession, case_id: str) -> CaseResponse:
        stmt = select(SuspiciousCase).where(SuspiciousCase.id == case_id).options(selectinload(SuspiciousCase.reviews))
        case = (await db.execute(stmt)).scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suspicious case not found")
        return CaseResponse(
            id=case.id,
            scan_id=case.scan_id,
            brand_id=case.brand_id,
            case_number=case.case_number,
            status=case.status,
            priority=case.priority,
            assigned_to=case.assigned_to,
            notes=case.notes,
            reviews=[CaseReviewResponse.model_validate(r) for r in case.reviews],
            created_at=case.created_at,
            updated_at=case.updated_at
        )

    @staticmethod
    async def add_review(
        db: AsyncSession,
        case_id: str,
        data: CaseReviewCreate,
        reviewer_id: str
    ) -> CaseResponse:
        stmt = select(SuspiciousCase).where(SuspiciousCase.id == case_id).options(selectinload(SuspiciousCase.reviews))
        case = (await db.execute(stmt)).scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suspicious case not found")

        old_status = case.status
        case.status = data.new_status

        review = CaseReview(
            case_id=case.id,
            reviewer_id=reviewer_id,
            previous_status=old_status,
            new_status=data.new_status,
            comments=data.comments
        )
        db.add(review)
        await db.flush()

        await log_audit_event(
            session=db,
            action="SUSPICIOUS_CASE_REVIEWED",
            resource_type="SUSPICIOUS_CASE",
            resource_id=case.id,
            user_id=reviewer_id,
            changes={"old_status": old_status, "new_status": data.new_status, "comments": data.comments}
        )
        await db.commit()
        db.expire_all()
        return await CaseService.get_case_by_id(db, case_id)
