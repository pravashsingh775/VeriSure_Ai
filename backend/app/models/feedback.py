from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import BaseModel


class FeedbackSample(BaseModel):
    __tablename__ = "feedback_samples"

    case_id = Column(String(36), ForeignKey("suspicious_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True)
    origin_type = Column(String(30), default="SCAN", nullable=False)  # SCAN, CASE, DATASET_REVIEW, REFERENCE_AUDIT

    verified_label = Column(String(50), nullable=False)
    # GENUINE, COUNTERFEIT_SUSPICIOUS, TAMPERED, DEFECTIVE

    dataset_category = Column(String(50), default="UNVERIFIED", nullable=False)
    # GENUINE_REFERENCE, GENUINE_CAPTURE, VERIFIED_SUSPICIOUS, SYNTHETIC_SUSPICIOUS, UNVERIFIED, REJECTED

    notes = Column(Text, nullable=True)
    verified_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_added_to_dataset = Column(Boolean, default=False, nullable=False)

    case = relationship("SuspiciousCase", back_populates="feedback")
