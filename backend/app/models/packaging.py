from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.app.core.database import BaseModel


class PackagingVersion(BaseModel):
    __tablename__ = "packaging_versions"

    pack_size_id = Column(String(36), ForeignKey("product_pack_sizes.id", ondelete="CASCADE"), nullable=False, index=True)
    version_code = Column(String(20), nullable=False)  # "V1", "V2", "V3"
    status = Column(String(30), default="DRAFT", nullable=False, index=True)  # DRAFT, PENDING_REVIEW, APPROVED, ACTIVE, DEPRECATED, ARCHIVED
    effective_start_date = Column(DateTime, nullable=True)
    effective_end_date = Column(DateTime, nullable=True)

    # Expected reference metadata for verification cross-checks
    expected_barcode = Column(String(50), nullable=True)  # EAN-13 code
    expected_fssai = Column(String(50), nullable=True)    # 14-digit FSSAI lic
    expected_mrp = Column(Float, nullable=True)
    expected_qr_pattern = Column(String(255), nullable=True) # Regex or domain pattern
    notes = Column(Text, nullable=True)

    created_by = Column(String(36), nullable=True)
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    pack_size = relationship("ProductPackSize", back_populates="packaging_versions")
    reference_images = relationship("ReferenceImage", back_populates="packaging_version", cascade="all, delete-orphan")
    reference_fingerprints = relationship("ReferenceFingerprint", back_populates="packaging_version", cascade="all, delete-orphan")

