import io

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_and_root():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "operational"

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"


def test_auth_login_and_me():
    # 1. Login with seeded admin
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@verisure.ai", "password": "Admin@12345"}
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert "PLATFORM_ADMIN" in data["roles"]
    admin_token = data["access_token"]

    # 2. Get me with token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@verisure.ai"
    assert me_res.json()["is_superuser"] is True

    # 3. Login with invalid password
    bad_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@verisure.ai", "password": "WrongPassword"}
    )
    assert bad_res.status_code == 401


def test_auth_register_new_consumer():
    import uuid
    email = f"consumer_{uuid.uuid4().hex[:6]}@verisure.ai"
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Test Consumer",
            "role_name": "CONSUMER"
        }
    )
    assert res.status_code == 201
    assert res.json()["email"] == email
    assert "CONSUMER" in res.json()["roles"]


def test_brands_and_rbac():
    import uuid
    # Consumer login
    c_login = client.post(
        "/api/v1/auth/login",
        json={"email": "consumer@verisure.ai", "password": "Consumer@12345"}
    )
    consumer_token = c_login.json()["access_token"]

    # Admin login
    a_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@verisure.ai", "password": "Admin@12345"}
    )
    admin_token = a_login.json()["access_token"]

    # 1. Public / Authenticated read brands
    brands_res = client.get("/api/v1/brands")
    assert brands_res.status_code == 200
    brands = brands_res.json()
    assert len(brands) >= 1
    amul = next(b for b in brands if b["code"] == "AMUL")
    assert amul["name"] == "Amul Dairy"

    # 2. Consumer forbidden from creating a brand
    forbidden_res = client.post(
        "/api/v1/brands",
        json={"name": "Fake Brand", "code": "FAKE"},
        headers={"Authorization": f"Bearer {consumer_token}"}
    )
    assert forbidden_res.status_code == 403

    # 3. Admin allowed to create a brand
    code = f"BRAND_{uuid.uuid4().hex[:6].upper()}"
    new_brand_res = client.post(
        "/api/v1/brands",
        json={"name": f"Test Brand {code}", "code": code, "is_verified": True},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert new_brand_res.status_code == 201
    assert new_brand_res.json()["code"] == code


def test_products_and_variants():
    # Fetch products
    res = client.get("/api/v1/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) >= 3

    taaza = next(p for p in products if p["name"] == "Amul Taaza")
    assert len(taaza["variants"]) >= 1
    variant = taaza["variants"][0]
    assert variant["variant_name"] == "Toned Milk"
    assert len(variant["pack_sizes"]) >= 2

    # Get single product
    single_res = client.get(f"/api/v1/products/{taaza['id']}")
    assert single_res.status_code == 200
    assert single_res.json()["id"] == taaza["id"]


def test_packaging_version_lifecycle_and_reference():
    # Admin login
    a_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@verisure.ai", "password": "Admin@12345"}
    )
    admin_token = a_login.json()["access_token"]

    # 1. Fetch pack size id for Amul Taaza 1L
    res = client.get("/api/v1/products")
    taaza = next(p for p in res.json() if p["name"] == "Amul Taaza")
    pack_size = next(ps for ps in taaza["variants"][0]["pack_sizes"] if ps["pack_size"] == "1L")

    # 2. Create new packaging version V2 (e.g. for upcoming 2027 design)
    v2_res = client.post(
        "/api/v1/packaging-versions",
        json={
            "pack_size_id": pack_size["id"],
            "version_code": "V2",
            "expected_barcode": "8901262010060",
            "expected_fssai": "10012021000071",
            "expected_mrp": 75.0,
            "notes": "2027 Eco-Friendly Tetra Pack redesign"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert v2_res.status_code == 201
    version_v2 = v2_res.json()
    assert version_v2["status"] == "DRAFT"
    assert version_v2["version_code"] == "V2"

    # 3. Upload reference image for V2
    dummy_image = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
    upload_res = client.post(
        "/api/v1/references/upload",
        data={
            "packaging_version_id": version_v2["id"],
            "view_type": "FRONT",
            "source_type": "BRAND_PROVIDED",
        },
        files={"file": ("reference_v2_front.png", dummy_image, "image/png")},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert upload_res.status_code == 201
    ref_image = upload_res.json()
    assert ref_image["approval_status"] == "PENDING"
    assert ref_image["trust_level"] == 1.0

    # 4. Approve reference image
    appr_res = client.put(
        f"/api/v1/references/{ref_image['id']}/approval",
        json={"approval_status": "APPROVED", "trust_level": 1.0},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["approval_status"] == "APPROVED"

    # 5. Activate Packaging Version V2
    act_res = client.put(
        f"/api/v1/packaging-versions/{version_v2['id']}/status?status=ACTIVE",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert act_res.status_code == 200
    assert act_res.json()["status"] == "ACTIVE"

    # 6. List references for version
    list_refs = client.get(f"/api/v1/references/version/{version_v2['id']}?only_approved=true")
    assert list_refs.status_code == 200
    assert len(list_refs.json()) == 1

    # Clean up test artifact from storage and db
    from backend.app.core.database import SyncSessionLocal
    from backend.app.core.storage import storage
    from backend.app.models.packaging import PackagingVersion
    from backend.app.models.reference import ReferenceImage
    storage.delete(ref_image["image_path"])
    with SyncSessionLocal() as session:
        ref_obj = session.query(ReferenceImage).filter(ReferenceImage.id == ref_image["id"]).first()
        if ref_obj:
            session.delete(ref_obj)
        pv_obj = session.query(PackagingVersion).filter(PackagingVersion.id == version_v2["id"]).first()
        if pv_obj:
            session.delete(pv_obj)
        session.commit()
