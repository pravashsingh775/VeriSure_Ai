from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluationRunResponse(BaseModel):
    id: str
    model_version_id: str
    dataset_version_id: Optional[str]
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1: Optional[float]
    roc_auc: Optional[float]
    confusion_matrix: Optional[Dict[str, Any]]
    robustness_metrics: Optional[Dict[str, Any]]
    evaluated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ModelVersionResponse(BaseModel):
    id: str
    model_id: str
    version_tag: str
    status: str # DEVELOPMENT, EVALUATED, APPROVED, CANARY, PRODUCTION, DEPRECATED, REJECTED
    artifact_path: Optional[str]
    hyperparameters: Dict[str, Any]
    evaluations: List[EvaluationRunResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelResponse(BaseModel):
    id: str
    name: str
    task: str
    architecture: str
    description: Optional[str]
    versions: List[ModelVersionResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelVersionCreate(BaseModel):
    version_tag: str = Field(min_length=2, max_length=50)
    status: str = "DEVELOPMENT"
    artifact_path: Optional[str] = None
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)


class EvaluationTriggerRequest(BaseModel):
    dataset_version_id: Optional[str] = None
    simulate_perturbations: bool = True

