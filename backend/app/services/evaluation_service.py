from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit import log_audit_event
from backend.app.models.model_registry import EvaluationRun, ModelVersionEntity
from backend.app.schemas.model_registry import EvaluationRunResponse


class EvaluationService:
    """
    Executes evaluation of registered AI models.
    Adheres strictly to scientific honesty: Does not fabricate synthetic benchmark accuracy.
    Clearly records when empirical physical datasets are not yet available.
    """
    @staticmethod
    async def run_evaluation(
        db: AsyncSession,
        model_version_id: str,
        dataset_version_id: str | None = None,
        simulate_perturbations: bool = False,
        actor_id: str | None = None
    ) -> EvaluationRunResponse:
        # 1. Verify model version
        mv = (await db.execute(select(ModelVersionEntity).where(ModelVersionEntity.id == model_version_id))).scalar_one_or_none()
        if not mv:
            raise ValueError("Model version not found")

        # 2. Honest Evaluation Status
        # Scientific Honesty: A real empirical benchmark dataset of physical milk packaging captures
        # is required before claiming verified accuracy, precision, recall, or ROC-AUC.
        eval_run = EvaluationRun(
            model_version_id=model_version_id,
            dataset_version_id=dataset_version_id,
            accuracy=None,
            precision=None,
            recall=None,
            f1=None,
            roc_auc=None,
            confusion_matrix={
                "status": "EMPIRICAL_DATASET_NOT_YET_AVAILABLE",
                "message": "Empirical dataset not yet available. Physical product validation remains future work."
            },
            robustness_metrics={
                "status": "PENDING_PHYSICAL_BENCHMARK",
                "message": "Physical environmental robustness metrics require verified real-world retail captures."
            },
            evaluated_at=datetime.utcnow()
        )
        db.add(eval_run)

        # Update model version status
        mv.status = "PENDING_EMPIRICAL_BENCHMARK"

        await log_audit_event(
            session=db,
            action="MODEL_EVALUATION_RECORDED",
            resource_type="MODEL_VERSION",
            resource_id=model_version_id,
            user_id=actor_id,
            changes={"status": "EMPIRICAL_DATASET_NOT_YET_AVAILABLE"}
        )
        await db.commit()
        await db.refresh(eval_run)

        return EvaluationRunResponse.model_validate(eval_run)
