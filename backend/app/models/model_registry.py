from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.app.core.database import BaseModel


class ModelEntity(BaseModel):
    __tablename__ = "ml_models"

    name = Column(String(100), unique=True, index=True, nullable=False)
    task = Column(String(100), nullable=False) # LOGO_VERIFIER, PACKAGING_SIMILARITY, FUSION_CALIBRATOR, OCR_EXTRACTOR
    architecture = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    versions = relationship("ModelVersionEntity", back_populates="model", cascade="all, delete-orphan")


class ModelVersionEntity(BaseModel):
    __tablename__ = "ml_model_versions"

    model_id = Column(String(36), ForeignKey("ml_models.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag = Column(String(50), nullable=False) # "v1.0.0"
    status = Column(String(50), default="DEVELOPMENT", nullable=False, index=True)
    # DEVELOPMENT, EVALUATED, APPROVED, CANARY, PRODUCTION, DEPRECATED, REJECTED

    artifact_path = Column(String(500), nullable=True)
    hyperparameters = Column(JSON, default=dict, nullable=False)

    model = relationship("ModelEntity", back_populates="versions")
    training_runs = relationship("TrainingRun", back_populates="model_version", cascade="all, delete-orphan")
    evaluation_runs = relationship("EvaluationRun", back_populates="model_version", cascade="all, delete-orphan")
    deployments = relationship("ModelDeployment", back_populates="model_version", cascade="all, delete-orphan")


class TrainingRun(BaseModel):
    __tablename__ = "ml_training_runs"

    model_version_id = Column(String(36), ForeignKey("ml_model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="PENDING", nullable=False) # PENDING, RUNNING, COMPLETED, FAILED
    metrics = Column(JSON, default=dict, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    model_version = relationship("ModelVersionEntity", back_populates="training_runs")


class EvaluationRun(BaseModel):
    __tablename__ = "ml_evaluation_runs"

    model_version_id = Column(String(36), ForeignKey("ml_model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True)

    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1 = Column(Float, nullable=True)
    roc_auc = Column(Float, nullable=True)

    confusion_matrix = Column(JSON, default=dict, nullable=True)
    robustness_metrics = Column(JSON, default=dict, nullable=True) # e.g. blur, glare, lighting perturbations
    evaluated_at = Column(DateTime, nullable=True)

    model_version = relationship("ModelVersionEntity", back_populates="evaluation_runs")


class ModelDeployment(BaseModel):
    __tablename__ = "ml_model_deployments"

    model_version_id = Column(String(36), ForeignKey("ml_model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    environment = Column(String(50), default="PRODUCTION", nullable=False)
    deployed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    model_version = relationship("ModelVersionEntity", back_populates="deployments")
