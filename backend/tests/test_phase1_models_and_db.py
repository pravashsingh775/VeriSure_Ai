import contextlib
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from backend.app.core.storage import LocalStorage
from backend.app.models import (
    AuditLog,
    Brand,
    BrandUser,
    Decision,
    Evidence,
    PackagingVersion,
    Product,
    ProductPackSize,
    ProductVariant,
    ReferenceImage,
    Role,
    Scan,
    ScanImage,
    SuspiciousCase,
    User,
    UserRole,
)


@pytest.fixture(scope="module")
def sync_db_session():
    test_db_url = "sqlite:///./test_phase1.db"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_phase1.db"):
        with contextlib.suppress(Exception):
            os.remove("./test_phase1.db")


def test_security_password_hashing():
    raw = "SecurePassword123!"
    hashed = get_password_hash(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_security_jwt_tokens():
    token = create_access_token(
        subject="user-uuid-123",
        email="test@verisure.ai",
        roles=["CONSUMER", "BRAND_ADMIN"],
        brand_id="brand-amul-123"
    )
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload.sub == "user-uuid-123"
    assert payload.email == "test@verisure.ai"
    assert "CONSUMER" in payload.roles
    assert "BRAND_ADMIN" in payload.roles
    assert payload.brand_id == "brand-amul-123"


def test_storage_local_operations(tmp_path):
    import asyncio

    async def _test():
        storage = LocalStorage(base_path=tmp_path)
        content = b"Sample Image File Content"
        rel_path, abs_path = await storage.save_bytes(content, "raw_scans", "test_sample.png")

        assert os.path.exists(abs_path)
        assert storage.exists(rel_path) is True

        # Path traversal prevention test
        with pytest.raises(ValueError, match="Illegal path traversal"):
            storage.get_absolute_path("../../etc/passwd")

        # Deletion test
        deleted = storage.delete(rel_path)
        assert deleted is True
        assert storage.exists(rel_path) is False

    asyncio.run(_test())


def test_database_model_hierarchy(sync_db_session):
    db = sync_db_session

    # 1. Create Role & User
    role_admin = Role(name="PLATFORM_ADMIN", description="System Platform Administrator")
    db.add(role_admin)
    db.commit()

    user = User(
        email="admin@verisure.ai",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Platform Admin",
        is_superuser=True
    )
    db.add(user)
    db.commit()

    user_role = UserRole(user_id=user.id, role_id=role_admin.id)
    db.add(user_role)
    db.commit()

    # 2. Create Brand & Product hierarchy
    brand = Brand(name="Amul Dairy", code="AMUL", is_verified=True)
    db.add(brand)
    db.commit()

    brand_user = BrandUser(brand_id=brand.id, user_id=user.id, role="ADMIN")
    db.add(brand_user)
    db.commit()

    product = Product(brand_id=brand.id, name="Amul Taaza", category="MILK")
    db.add(product)
    db.commit()

    variant = ProductVariant(product_id=product.id, variant_name="Toned Milk", fat_content="3.0% min")
    db.add(variant)
    db.commit()

    pack_size = ProductPackSize(variant_id=variant.id, pack_size="1L", pack_type="TETRA_PACK", net_quantity="1000 ml")
    db.add(pack_size)
    db.commit()

    pkg_version = PackagingVersion(
        pack_size_id=pack_size.id,
        version_code="V1",
        status="ACTIVE",
        expected_barcode="8901262010053",
        expected_fssai="10012021000071",
        expected_mrp=72.0
    )
    db.add(pkg_version)
    db.commit()

    # 3. Create Reference Image
    ref_img = ReferenceImage(
        packaging_version_id=pkg_version.id,
        view_type="FRONT",
        image_path="references/amul_taaza_1l_v1_front.png",
        source_type="BRAND_APPROVED",
        trust_level=1.0,
        approval_status="APPROVED"
    )
    db.add(ref_img)
    db.commit()

    # 4. Create Scan and Scan Image
    scan = Scan(
        user_id=user.id,
        status="DECISION",
        identified_product_id=product.id,
        identified_packaging_version_id=pkg_version.id,
        matched_reference_id=ref_img.id
    )
    db.add(scan)
    db.commit()

    scan_img = ScanImage(
        scan_id=scan.id,
        view_type="FRONT",
        image_path="raw_scans/scan_001_front.png",
        quality_score=0.92,
        quality_details={"resolution": 0.95, "blur": 0.88, "usable": True}
    )
    db.add(scan_img)
    db.commit()

    # 5. Create Evidence
    ev_logo = Evidence(
        scan_id=scan.id,
        evidence_type="logo",
        score=0.94,
        confidence=0.91,
        availability=True,
        quality=0.92,
        source="verisure-logo-orb-v1",
        explanation="Logo geometry and colors match reference with 94% confidence.",
        features={"inliers": 42},
        warnings=[]
    )
    db.add(ev_logo)
    db.commit()

    # 6. Create Decision
    decision = Decision(
        scan_id=scan.id,
        decision_state="LOW_RISK",
        risk_score=12.5,
        confidence=0.91,
        uncertainty=0.09,
        evidence_coverage=0.95,
        recommendation="Product visual features strongly match genuine reference. Safe to consume.",
        reason_codes=["LOGO_CONGRUENT", "BARCODE_VERIFIED"],
        explanation_summary="Evidence indicates consistent packaging layout, typography, and logo.",
        contradictions=[]
    )
    db.add(decision)
    db.commit()

    # 7. Create Suspicious Case
    case = SuspiciousCase(
        scan_id=scan.id,
        brand_id=brand.id,
        case_number="CASE-AMUL-2026-0001",
        status="OPEN",
        priority="LOW"
    )
    db.add(case)
    db.commit()

    # 8. Create Audit Log
    audit = AuditLog(
        user_id=user.id,
        action="TEST_CASE_INITIALIZED",
        resource_type="CASE",
        resource_id=case.id,
        changes={"status": "OPEN"}
    )
    db.add(audit)
    db.commit()

    # Query verification
    retrieved_scan = db.query(Scan).filter(Scan.id == scan.id).first()
    assert retrieved_scan is not None
    assert len(retrieved_scan.images) == 1
    assert len(retrieved_scan.evidences) == 1
    assert retrieved_scan.decision.decision_state == "LOW_RISK"
    assert retrieved_scan.decision.risk_score == 12.5
    assert retrieved_scan.suspicious_case.case_number == "CASE-AMUL-2026-0001"
