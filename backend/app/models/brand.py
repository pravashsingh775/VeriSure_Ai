from sqlalchemy import Boolean, Column, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import BaseModel


class Brand(BaseModel):
    __tablename__ = "brands"

    name = Column(String(100), unique=True, index=True, nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)  # e.g. "AMUL"
    description = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)

    products = relationship("Product", back_populates="brand", cascade="all, delete-orphan")
    brand_users = relationship("BrandUser", back_populates="brand", cascade="all, delete-orphan")
    settings = relationship("BrandSettings", back_populates="brand", uselist=False, cascade="all, delete-orphan")
    cases = relationship("SuspiciousCase", back_populates="brand")


class BrandUser(BaseModel):
    __tablename__ = "brand_users"

    brand_id = Column(String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="MEMBER", nullable=False)  # OWNER, ADMIN, REVIEWER, MEMBER

    brand = relationship("Brand", back_populates="brand_users")
    user = relationship("User", back_populates="brand_memberships")


class BrandSettings(BaseModel):
    __tablename__ = "brand_settings"

    brand_id = Column(String(36), ForeignKey("brands.id", ondelete="CASCADE"), unique=True, nullable=False)
    auto_triage_threshold = Column(Float, default=70.0, nullable=False)  # Risk score threshold to auto-create case
    allowed_domains = Column(Text, nullable=True)  # Comma-separated trusted QR domains
    notification_email = Column(String(255), nullable=True)

    brand = relationship("Brand", back_populates="settings")
