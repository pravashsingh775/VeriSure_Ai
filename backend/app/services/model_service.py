from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.audit import log_audit_event
from backend.app.models.model_registry import ModelDeployment, ModelEntity, ModelVersionEntity
from backend.app.schemas.model_registry import (
    EvaluationRunResponse,
    ModelResponse,
    ModelVersionCreate,
    ModelVersionResponse,
)


class ModelService:
    @staticmethod
    async def list_models(db: AsyncSession) -> List[ModelResponse]:
        stmt = select(ModelEntity).options(
            selectinload(ModelEntity.versions).selectinload(ModelVersionEntity.evaluation_runs)
        )
        result = await db.execute(stmt)
        models = result.scalars().all()

        responses: List[ModelResponse] = []
        for m in models:
            versions = []
            for v in m.versions:
                evals = [EvaluationRunResponse.model_validate(e) for e in v.evaluation_runs]
                versions.append(ModelVersionResponse(
                    id=v.id,
                    model_id=v.model_id,
                    version_tag=v.version_tag,
                    status=v.status,
                    artifact_path=v.artifact_path,
                    hyperparameters=v.hyperparameters or {},
                    evaluations=evals,
                    created_at=v.created_at
                ))
            responses.append(ModelResponse(
                id=m.id,
                name=m.name,
                task=m.task,
                architecture=m.architecture,
                description=m.description,
                versions=versions,
                created_at=m.created_at
            ))
        return responses

    @staticmethod
    async def create_version(
        db: AsyncSession,
        model_id: str,
        data: ModelVersionCreate,
        actor_id: Optional[str] = None
    ) -> ModelVersionResponse:
        model = (await db.execute(select(ModelEntity).where(ModelEntity.id == model_id))).scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model entity not found")

        version = ModelVersionEntity(
            model_id=model_id,
            version_tag=data.version_tag,
            status=data.status,
            artifact_path=data.artifact_path,
            hyperparameters=data.hyperparameters
        )
        db.add(version)
        await db.flush()

        await log_audit_event(
            session=db,
            action="MODEL_VERSION_REGISTERED",
            resource_type="MODEL_VERSION",
            resource_id=version.id,
            user_id=actor_id,
            changes={"version_tag": version.version_tag, "status": version.status}
        )
        await db.commit()
        return ModelVersionResponse(
            id=version.id,
            model_id=version.model_id,
            version_tag=version.version_tag,
            status=version.status,
            artifact_path=version.artifact_path,
            hyperparameters=version.hyperparameters or {},
            evaluations=[],
            created_at=version.created_at
        )

    @staticmethod
    async def update_status(
        db: AsyncSession,
        version_id: str,
        new_status: str,
        actor_id: Optional[str] = None
    ) -> ModelVersionResponse:
        valid_statuses = ["DEVELOPMENT", "EVALUATED", "APPROVED", "CANARY", "PRODUCTION", "DEPRECATED", "REJECTED"]
        new_status = new_status.upper()
        if new_status not in valid_statuses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status '{new_status}'")

        stmt = select(ModelVersionEntity).where(ModelVersionEntity.id == version_id).options(selectinload(ModelVersionEntity.evaluation_runs))
        version = (await db.execute(stmt)).scalar_one_or_none()
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found")

        old_status = version.status
        version.status = new_status

        if new_status == "PRODUCTION":
            deployment = ModelDeployment(
                model_version_id=version.id,
                environment="PRODUCTION",
                is_active=True
            )
            db.add(deployment)

        await log_audit_event(
            session=db,
            action="MODEL_VERSION_STATUS_CHANGED",
            resource_type="MODEL_VERSION",
            resource_id=version.id,
            user_id=actor_id,
            changes={"old_status": old_status, "new_status": new_status}
        )
        await db.commit()
        evals = [EvaluationRunResponse.model_validate(e) for e in version.evaluation_runs]
        return ModelVersionResponse(
            id=version.id,
            model_id=version.model_id,
            version_tag=version.version_tag,
            status=version.status,
            artifact_path=version.artifact_path,
            hyperparameters=version.hyperparameters or {},
            evaluations=evals,
            created_at=version.created_at
        )

