from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.core.database import BaseModel


class Dataset(BaseModel):
    __tablename__ = "datasets"

    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    domain_tag = Column(String(50), default="AMUL_DAIRY", nullable=False)

    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan", lazy="selectin")


class DatasetVersion(BaseModel):
    __tablename__ = "dataset_versions"

    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag = Column(String(50), nullable=False) # e.g. "v1.0.0"
    split_strategy = Column(String(100), default="PACKAGE_AND_SESSION_ISOLATED", nullable=False)

    train_count = Column(Integer, default=0, nullable=False)
    val_count = Column(Integer, default=0, nullable=False)
    test_count = Column(Integer, default=0, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)

    dataset = relationship("Dataset", back_populates="versions")
    samples = relationship("DatasetSample", back_populates="dataset_version", cascade="all, delete-orphan", lazy="selectin")


class DatasetSample(BaseModel):
    __tablename__ = "dataset_samples"

    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    image_path = Column(String(500), nullable=False)
    label = Column(String(50), nullable=False) # GENUINE, SUSPICIOUS, TAMPERED
    split = Column(String(20), default="TRAIN", nullable=False) # TRAIN, VAL, TEST

    # Data leakage prevention identifiers
    package_id = Column(String(100), nullable=True)
    capture_session_id = Column(String(100), nullable=True)

    dataset_version = relationship("DatasetVersion", back_populates="samples")
