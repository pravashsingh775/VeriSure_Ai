from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit import log_audit_event
from backend.app.models.feedback import FeedbackSample
from backend.app.schemas.feedback import FeedbackCreate, FeedbackResponse


class FeedbackService:
    @staticmethod
    async def record_feedback(
        db: AsyncSession,
        data: FeedbackCreate,
        verified_by_id: str
    ) -> FeedbackResponse:
        sample = FeedbackSample(
            scan_id=data.scan_id,
            case_id=data.case_id,
            verified_label=data.verified_label,
            dataset_category=data.dataset_category,
            notes=data.notes,
            verified_by=verified_by_id,
            is_added_to_dataset=False
        )
        db.add(sample)
        await db.flush()

        await log_audit_event(
            session=db,
            action="FEEDBACK_VERIFIED_LABEL_RECORDED",
            resource_type="FEEDBACK_SAMPLE",
            resource_id=sample.id,
            user_id=verified_by_id,
            changes={"verified_label": data.verified_label, "category": data.dataset_category}
        )
        await db.commit()
        return FeedbackResponse.model_validate(sample)

    @staticmethod
    async def list_feedback(db: AsyncSession) -> list[FeedbackResponse]:
        stmt = select(FeedbackSample).order_by(FeedbackSample.created_at.desc())
        result = await db.execute(stmt)
        samples = result.scalars().all()
        return [FeedbackResponse.model_validate(s) for s in samples]

