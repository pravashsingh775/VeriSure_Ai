from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: Optional[str] = None
    domain_tag: str = "AMUL_DAIRY"


class DatasetSampleCreate(BaseModel):
    image_path: str
    label: str = Field(pattern="^(GENUINE|SUSPICIOUS|TAMPERED)$")
    split: str = Field(default="TRAIN", pattern="^(TRAIN|VAL|TEST)$")
    package_id: Optional[str] = None
    capture_session_id: Optional[str] = None


class DatasetVersionCreate(BaseModel):
    version_tag: str = Field(min_length=2, max_length=50) # e.g. "v1.0.0"
    split_strategy: str = "PACKAGE_AND_SESSION_ISOLATED"
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    samples: List[DatasetSampleCreate] = []


class DatasetVersionResponse(BaseModel):
    id: str
    dataset_id: str
    version_tag: str
    split_strategy: str
    train_count: int
    val_count: int
    test_count: int
    is_locked: bool
    metadata_json: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    domain_tag: str
    versions: List[DatasetVersionResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}

