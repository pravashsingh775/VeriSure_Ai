from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.app.core.database import BaseModel


class Product(BaseModel):
    __tablename__ = "products"

    brand_id = Column(String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    category = Column(String(100), default="MILK", nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    brand = relationship("Brand", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


class ProductVariant(BaseModel):
    __tablename__ = "product_variants"

    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_name = Column(String(100), nullable=False)  # e.g. "Taaza", "Gold", "Cow Milk"
    fat_content = Column(String(50), nullable=True)     # e.g. "3.0% min"
    snf_content = Column(String(50), nullable=True)     # e.g. "8.5% min"
    description = Column(Text, nullable=True)

    product = relationship("Product", back_populates="variants")
    pack_sizes = relationship("ProductPackSize", back_populates="variant", cascade="all, delete-orphan")


class ProductPackSize(BaseModel):
    __tablename__ = "product_pack_sizes"

    variant_id = Column(String(36), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    pack_size = Column(String(50), nullable=False)   # e.g. "500ml", "1L"
    pack_type = Column(String(50), default="POUCH", nullable=False)  # POUCH, TETRA_PACK, BOTTLE, CUP
    net_quantity = Column(String(50), nullable=True) # e.g. "500 ml", "1000 ml"

    variant = relationship("ProductVariant", back_populates="pack_sizes")
    packaging_versions = relationship("PackagingVersion", back_populates="pack_size", cascade="all, delete-orphan")

