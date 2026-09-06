from backend.app.core.database import Base, BaseModel
from backend.app.models.audit import AuditLog
from backend.app.models.brand import Brand, BrandSettings, BrandUser
from backend.app.models.case import CaseReview, SuspiciousCase
from backend.app.models.dataset import Dataset, DatasetSample, DatasetVersion
from backend.app.models.decision import Decision
from backend.app.models.evidence import Evidence, PackagingFingerprintRecord
from backend.app.models.feedback import FeedbackSample
from backend.app.models.model_registry import (
    EvaluationRun,
    ModelDeployment,
    ModelEntity,
    ModelVersionEntity,
    TrainingRun,
)
from backend.app.models.packaging import PackagingVersion
from backend.app.models.product import Product, ProductPackSize, ProductVariant
from backend.app.models.reference import ReferenceFeature, ReferenceFingerprint, ReferenceImage
from backend.app.models.report import ReportRecord
from backend.app.models.scan import Scan, ScanImage
from backend.app.models.user import Permission, Role, RolePermission, User, UserRole

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "Brand",
    "BrandUser",
    "BrandSettings",
    "Product",
    "ProductVariant",
    "ProductPackSize",
    "PackagingVersion",
    "ReferenceImage",
    "ReferenceFeature",
    "ReferenceFingerprint",
    "Scan",
    "ScanImage",
    "Evidence",
    "PackagingFingerprintRecord",
    "Decision",
    "SuspiciousCase",
    "CaseReview",
    "FeedbackSample",
    "Dataset",
    "DatasetVersion",
    "DatasetSample",
    "ModelEntity",
    "ModelVersionEntity",
    "TrainingRun",
    "EvaluationRun",
    "ModelDeployment",
    "ReportRecord",
    "AuditLog",
]
