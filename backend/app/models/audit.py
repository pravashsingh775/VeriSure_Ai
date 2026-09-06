from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String

from backend.app.core.database import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True) # e.g. "REFERENCE_APPROVED", "CASE_TRIAGED"
    resource_type = Column(String(50), nullable=False, index=True) # e.g. "REFERENCE", "PACKAGING_VERSION"
    resource_id = Column(String(36), nullable=True)
    changes = Column(JSON, default=dict, nullable=False)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
