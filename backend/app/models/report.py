from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from backend.app.core.database import BaseModel


class ReportRecord(BaseModel):
    __tablename__ = "reports"

    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False)
    pdf_path = Column(String(500), nullable=False)
    pdf_sha256 = Column(String(64), nullable=True)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    generated_at = Column(DateTime, nullable=False)

    scan = relationship("Scan", back_populates="report")

