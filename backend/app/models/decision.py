from sqlalchemy import Column, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import BaseModel


class Decision(BaseModel):
    __tablename__ = "decisions"

    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False)

    decision_state = Column(String(50), nullable=False, index=True)
    # LIKELY_GENUINE, LOW_RISK, MEDIUM_RISK, HIGH_RISK, CRITICAL_RISK, INSUFFICIENT_EVIDENCE, UNSUPPORTED_PRODUCT, TAMPERED_OR_DAMAGED

    risk_score = Column(Float, nullable=False)          # 0 to 100 risk scale
    confidence = Column(Float, nullable=False)          # 0.0 to 1.0 overall assessment confidence
    uncertainty = Column(Float, nullable=False)         # 0.0 to 1.0 epistemic & aleatoric uncertainty
    evidence_coverage = Column(Float, nullable=False)   # 0.0 to 1.0 proportion of expected evidence evaluated

    recommendation = Column(Text, nullable=False)       # Consumer advice (e.g. safe to consume, check seal, report)
    reason_codes = Column(JSON, default=list, nullable=False)      # Machine-readable tags e.g. ["LOGO_MATCH", "BARCODE_VERIFIED"]
    explanation_summary = Column(Text, nullable=False)  # Grounded human-readable synthesis
    contradictions = Column(JSON, default=list, nullable=False)   # Identified conflicts across evidence types

    scan = relationship("Scan", back_populates="decision")
