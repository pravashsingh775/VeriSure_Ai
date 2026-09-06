from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.app.core.database import BaseModel


class Evidence(BaseModel):
    __tablename__ = "evidences"

    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type = Column(String(50), nullable=False, index=True)
    # logo, layout, colour, typography, texture, shape, seal, print, packaging, ocr, barcode, qr, certification

    score = Column(Float, nullable=True)         # 0.0 to 1.0 similarity/authenticity score, or NULL if unavailable
    confidence = Column(Float, nullable=False)   # 0.0 to 1.0 confidence in model prediction
    availability = Column(Boolean, default=True, nullable=False)
    quality = Column(Float, default=1.0, nullable=False)       # 0.0 to 1.0 quality of image region for this evidence

    source = Column(String(100), nullable=False) # e.g. "verisure-logo-orb-v1"
    reference_id = Column(String(36), nullable=True)
    model_version = Column(String(50), default="v1.0", nullable=False)

    features = Column(JSON, default=dict, nullable=False)
    regions = Column(JSON, default=list, nullable=False)       # [{x_min, y_min, x_max, y_max, difference_score, explanation}]
    explanation = Column(Text, nullable=False)
    warnings = Column(JSON, default=list, nullable=False)

    scan = relationship("Scan", back_populates="evidences")


class PackagingFingerprintRecord(BaseModel):
    __tablename__ = "packaging_fingerprints"

    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False)
    fingerprint_json = Column(JSON, nullable=False)

    scan = relationship("Scan", back_populates="fingerprint")
