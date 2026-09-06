
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.model_registry import (
    EvaluationRunResponse,
    EvaluationTriggerRequest,
    ModelResponse,
    ModelVersionCreate,
    ModelVersionResponse,
)
from backend.app.services.evaluation_service import EvaluationService
from backend.app.services.model_service import ModelService

router = APIRouter()


@router.get("", response_model=list[ModelResponse])
async def list_registered_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN", "BRAND_ADMIN"]))
):
    """
    List registered AI models, active versions, and evaluation benchmarks.
    """
    return await ModelService.list_models(db)


@router.post("/{model_id}/versions", response_model=ModelVersionResponse, status_code=201)
async def create_model_version(
    model_id: str,
    data: ModelVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN"]))
):
    """
    Registers a new version of an AI model architecture.
    """
    return await ModelService.create_version(db, model_id, data, actor_id=current_user.id)


@router.put("/versions/{version_id}/status", response_model=ModelVersionResponse)
async def update_model_version_status(
    version_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN"]))
):
    """
    Transition model version status (e.g. APPROVED, CANARY, PRODUCTION, DEPRECATED).
    """
    return await ModelService.update_status(db, version_id, new_status=status, actor_id=current_user.id)


@router.post("/versions/{version_id}/evaluate", response_model=EvaluationRunResponse)
async def run_model_evaluation(
    version_id: str,
    data: EvaluationTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["PLATFORM_ADMIN"]))
):
    """
    Triggers an evaluation run calculating accuracy, precision, recall, F1,
    ROC-AUC, and robustness degradation metrics under simulated physical perturbations.
    """
    return await EvaluationService.run_evaluation(
        db=db,
        model_version_id=version_id,
        dataset_version_id=data.dataset_version_id,
        simulate_perturbations=data.simulate_perturbations,
        actor_id=current_user.id
    )
