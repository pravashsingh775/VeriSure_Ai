from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import BaseModel


class Scan(BaseModel):
    __tablename__ = "scans"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), default="CREATED", nullable=False, index=True)
    # CREATED -> UPLOADED -> QUALITY_CHECK -> ANALYZING -> REFERENCE_RETRIEVAL -> EVIDENCE_ANALYSIS -> FUSION -> DECISION -> REPORT_READY (or FAILED)

    # Candidate identification
    identified_product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    identified_packaging_version_id = Column(String(36), ForeignKey("packaging_versions.id", ondelete="SET NULL"), nullable=True)
    matched_reference_id = Column(String(36), ForeignKey("reference_images.id", ondelete="SET NULL"), nullable=True)

    total_images = Column(Integer, default=1, nullable=False)
    is_multi_angle = Column(Boolean, default=False, nullable=False)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="scans")
    images = relationship("ScanImage", back_populates="scan", cascade="all, delete-orphan", order_by="ScanImage.created_at")
    evidences = relationship("Evidence", back_populates="scan", cascade="all, delete-orphan")
    decision = relationship("Decision", back_populates="scan", uselist=False, cascade="all, delete-orphan")
    fingerprint = relationship("PackagingFingerprintRecord", back_populates="scan", uselist=False, cascade="all, delete-orphan")
    report = relationship("ReportRecord", back_populates="scan", uselist=False, cascade="all, delete-orphan")
    suspicious_case = relationship("SuspiciousCase", back_populates="scan", uselist=False)


class ScanImage(BaseModel):
    __tablename__ = "scan_images"

    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    view_type = Column(String(20), default="FRONT", nullable=False) # FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM, UNKNOWN
    image_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=True)

    # Image Quality Assessment
    quality_score = Column(Float, nullable=True)
    quality_details = Column(JSON, nullable=True) # {"resolution": 0.9, "blur": 0.85, "brightness": 0.9, "glare": 0.8, "usable": true}

    # Product Detection & Crops
    detected_bbox = Column(JSON, nullable=True) # [ymin, xmin, ymax, xmax] normalized
    crop_path = Column(String(500), nullable=True)
    heatmap_path = Column(String(500), nullable=True)

    scan = relationship("Scan", back_populates="images")

