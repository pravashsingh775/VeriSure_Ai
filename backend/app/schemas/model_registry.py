from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvaluationRunResponse(BaseModel):
    id: str
    model_version_id: str
    dataset_version_id: str | None
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    roc_auc: float | None
    confusion_matrix: dict[str, Any] | None
    robustness_metrics: dict[str, Any] | None
    evaluated_at: datetime | None

    model_config = {"from_attributes": True}


class ModelVersionResponse(BaseModel):
    id: str
    model_id: str
    version_tag: str
    status: str # DEVELOPMENT, EVALUATED, APPROVED, CANARY, PRODUCTION, DEPRECATED, REJECTED
    artifact_path: str | None
    hyperparameters: dict[str, Any]
    evaluations: list[EvaluationRunResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelResponse(BaseModel):
    id: str
    name: str
    task: str
    architecture: str
    description: str | None
    versions: list[ModelVersionResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelVersionCreate(BaseModel):
    version_tag: str = Field(min_length=2, max_length=50)
    status: str = "DEVELOPMENT"
    artifact_path: str | None = None
    hyperparameters: dict[str, Any] = Field(default_factory=dict)


class EvaluationTriggerRequest(BaseModel):
    dataset_version_id: str | None = None
    simulate_perturbations: bool = True

