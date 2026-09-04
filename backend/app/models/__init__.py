from backend.app.core.database import Base, BaseModel
from backend.app.models.user import User, Role, Permission, UserRole, RolePermission
from backend.app.models.brand import Brand, BrandUser, BrandSettings
from backend.app.models.product import Product, ProductVariant, ProductPackSize
from backend.app.models.packaging import PackagingVersion
from backend.app.models.reference import ReferenceImage, ReferenceFeature, ReferenceFingerprint
from backend.app.models.scan import Scan, ScanImage
from backend.app.models.evidence import Evidence, PackagingFingerprintRecord
from backend.app.models.decision import Decision
from backend.app.models.case import SuspiciousCase, CaseReview
from backend.app.models.feedback import FeedbackSample
from backend.app.models.dataset import Dataset, DatasetVersion, DatasetSample
from backend.app.models.model_registry import (
    ModelEntity,
    ModelVersionEntity,
    TrainingRun,
    EvaluationRun,
    ModelDeployment,
)
from backend.app.models.report import ReportRecord
from backend.app.models.audit import AuditLog

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
