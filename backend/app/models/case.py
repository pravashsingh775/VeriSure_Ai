from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import BaseModel


class SuspiciousCase(BaseModel):
    __tablename__ = "suspicious_cases"

    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False)
    brand_id = Column(String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)

    case_number = Column(String(50), unique=True, index=True, nullable=False)
    status = Column(String(50), default="OPEN", nullable=False, index=True)
    # OPEN -> UNDER_REVIEW -> NEEDS_MORE_EVIDENCE -> VERIFIED_GENUINE -> VERIFIED_SUSPICIOUS -> REJECTED -> CLOSED

    priority = Column(String(20), default="MEDIUM", nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    assigned_to = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    scan = relationship("Scan", back_populates="suspicious_case")
    brand = relationship("Brand", back_populates="cases")
    reviews = relationship("CaseReview", back_populates="case", cascade="all, delete-orphan", order_by="CaseReview.created_at", lazy="selectin")
    feedback = relationship("FeedbackSample", back_populates="case", uselist=False)


class CaseReview(BaseModel):
    __tablename__ = "case_reviews"

    case_id = Column(String(36), ForeignKey("suspicious_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    previous_status = Column(String(50), nullable=False)
    new_status = Column(String(50), nullable=False)
    comments = Column(Text, nullable=True)

    case = relationship("SuspiciousCase", back_populates="reviews")
