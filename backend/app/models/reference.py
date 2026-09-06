from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from backend.app.core.database import BaseModel


class ReferenceImage(BaseModel):
    __tablename__ = "reference_images"

    packaging_version_id = Column(String(36), ForeignKey("packaging_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    view_type = Column(String(20), default="FRONT", nullable=False)  # FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM
    image_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=True)

    # Source provenance & Trust Level
    source_type = Column(String(50), default="OFFICIAL_BRAND_ORIGIN", nullable=False)  # OFFICIAL_BRAND_ORIGIN, VERIFIED_GENUINE_SAMPLE, SYNTHETIC_TEST_STUB, VERIFIED_COUNTERFEIT_SAMPLE
    source_document = Column(String(500), nullable=True)  # URL or document spec reference
    captured_at = Column(DateTime, nullable=True)
    trust_level = Column(Float, default=1.0, nullable=False)  # 0.0 - 1.0 trust weighting
    approval_status = Column(String(30), default="APPROVED", nullable=False, index=True)  # PENDING, APPROVED, REJECTED
    verification_status = Column(String(30), default="VERIFIED", nullable=False)  # UNVERIFIED, VERIFIED, REJECTED

    uploaded_by = Column(String(36), nullable=True)
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    packaging_version = relationship("PackagingVersion", back_populates="reference_images")
    features = relationship("ReferenceFeature", back_populates="reference_image", cascade="all, delete-orphan")


class ReferenceFeature(BaseModel):
    __tablename__ = "reference_features"

    reference_image_id = Column(String(36), ForeignKey("reference_images.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_type = Column(String(50), nullable=False, index=True)  # LOGO, COLOR_PALETTE, LAYOUT_GRAPH, TEXTURE_LBP, ORB_KEYPOINTS
    feature_data = Column(JSON, nullable=False)

    reference_image = relationship("ReferenceImage", back_populates="features")


class ReferenceFingerprint(BaseModel):
    __tablename__ = "reference_fingerprints"

    packaging_version_id = Column(String(36), ForeignKey("packaging_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    model_version = Column(String(50), default="v1.0", nullable=False)
    fingerprint_json = Column(JSON, nullable=False)

    packaging_version = relationship("PackagingVersion", back_populates="reference_fingerprints")

