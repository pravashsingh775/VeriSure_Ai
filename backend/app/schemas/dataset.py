from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str | None = None
    domain_tag: str = "AMUL_DAIRY"


class DatasetSampleCreate(BaseModel):
    image_path: str
    label: str = Field(pattern="^(GENUINE|SUSPICIOUS|TAMPERED)$")
    split: str = Field(default="TRAIN", pattern="^(TRAIN|VAL|TEST)$")
    package_id: str | None = None
    capture_session_id: str | None = None


class DatasetVersionCreate(BaseModel):
    version_tag: str = Field(min_length=2, max_length=50) # e.g. "v1.0.0"
    split_strategy: str = "PACKAGE_AND_SESSION_ISOLATED"
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    samples: list[DatasetSampleCreate] = []


class DatasetVersionResponse(BaseModel):
    id: str
    dataset_id: str
    version_tag: str
    split_strategy: str
    train_count: int
    val_count: int
    test_count: int
    is_locked: bool
    metadata_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    id: str
    name: str
    description: str | None
    domain_tag: str
    versions: list[DatasetVersionResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}

