import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.core.security import get_password_hash
from backend.app.main import app
from backend.app.models import Brand, BrandUser, Role, User, UserRole

client = TestClient(app)

def get_token_for(email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]

@pytest.fixture(scope="module")
def tokens():
    return {
        "admin": get_token_for("admin@verisure.ai", "Admin@12345"),
        "amul_admin": get_token_for("amul_admin@verisure.ai", "Amul@12345"),
        "amul_reviewer": get_token_for("amul_reviewer@verisure.ai", "Reviewer@12345"),
        "consumer": get_token_for("consumer@verisure.ai", "Consumer@12345"),
    }

def test_auth_invalid_credentials():
    res = client.post("/api/v1/auth/login", json={"email": "admin@verisure.ai", "password": "WrongPassword"})
    assert res.status_code == 401

    res = client.post("/api/v1/auth/login", json={"email": "nonexistent_attacker@evil.com", "password": "AnyPassword"})
    assert res.status_code == 401

def test_auth_malformed_and_missing_tokens():
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401

    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer NOT_A_REAL_JWT_TOKEN"})
    assert res.status_code == 401

    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "})
    assert res.status_code == 401

def test_auth_privilege_escalation_guard(tokens):
    res = client.get("/api/v1/audit", headers={"Authorization": f"Bearer {tokens['consumer']}"})
    assert res.status_code == 403

    res = client.post(
        f"/api/v1/models/{uuid.uuid4()}/versions",
        json={"version_tag": "v999", "architecture": "TEST"},
        headers={"Authorization": f"Bearer {tokens['consumer']}"}
    )
    assert res.status_code == 403

    res = client.post(
        "/api/v1/brands",
        json={"name": "Evil Brand", "code": "EVIL"},
        headers={"Authorization": f"Bearer {tokens['consumer']}"}
    )
    assert res.status_code == 403

def test_rbac_authorization_matrix(tokens):
    matrix = [
        ("GET", "/api/v1/audit", None, {"unauth": 401, "consumer": 403, "amul_reviewer": 403, "amul_admin": 403, "admin": 200}),
        ("GET", "/api/v1/cases", None, {"unauth": 401, "consumer": 403, "amul_reviewer": 200, "amul_admin": 200, "admin": 200}),
        ("GET", "/api/v1/models", None, {"unauth": 401, "consumer": 403, "amul_reviewer": 403, "amul_admin": 200, "admin": 200}),
        ("GET", "/api/v1/analytics/admin", None, {"unauth": 401, "consumer": 403, "amul_reviewer": 200, "amul_admin": 200, "admin": 200}),
        ("GET", "/api/v1/analytics/consumer", None, {"unauth": 401, "consumer": 200, "amul_reviewer": 200, "amul_admin": 200, "admin": 200}),
    ]

    for method, path, body, expected in matrix:
        r_unauth = client.request(method, path, json=body)
        assert r_unauth.status_code == expected["unauth"], f"Failed {path} for unauth: got {r_unauth.status_code}"

        r_cons = client.request(method, path, json=body, headers={"Authorization": f"Bearer {tokens['consumer']}"})
        assert r_cons.status_code == expected["consumer"], f"Failed {path} for consumer: got {r_cons.status_code}"

        r_rev = client.request(method, path, json=body, headers={"Authorization": f"Bearer {tokens['amul_reviewer']}"})
        assert r_rev.status_code == expected["amul_reviewer"], f"Failed {path} for reviewer: got {r_rev.status_code}"

        r_ba = client.request(method, path, json=body, headers={"Authorization": f"Bearer {tokens['amul_admin']}"})
        assert r_ba.status_code == expected["amul_admin"], f"Failed {path} for brand admin: got {r_ba.status_code}"

        r_pa = client.request(method, path, json=body, headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert r_pa.status_code == expected["admin"], f"Failed {path} for platform admin: got {r_pa.status_code}"

@pytest.mark.anyio
async def test_multitenant_cross_brand_isolation(tokens):
    unique_suffix = uuid.uuid4().hex[:6]
    brand_b_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    brand_b_email = f"brandb_admin_{unique_suffix}@competitor.com"
    brand_b_pwd = "Password@123"

    async with AsyncSessionLocal() as session:
        brand_b = Brand(
            id=brand_b_id,
            name=f"Competitor Dairy {unique_suffix}",
            code=f"COMP_{unique_suffix.upper()}",
            is_verified=True
        )
        session.add(brand_b)

        user_b = User(
            id=user_b_id,
            email=brand_b_email,
            hashed_password=get_password_hash(brand_b_pwd),
            full_name="Competitor Lead",
            is_active=True,
            is_superuser=False
        )
        session.add(user_b)
        await session.flush()

        role_ba = (await session.execute(select(Role).where(Role.name == "BRAND_ADMIN"))).scalar_one()
        session.add(UserRole(user_id=user_b.id, role_id=role_ba.id))
        session.add(BrandUser(brand_id=brand_b.id, user_id=user_b.id, role="ADMIN"))
        await session.commit()

    token_b = get_token_for(brand_b_email, brand_b_pwd)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    r_anal = client.get("/api/v1/analytics/brand/AMUL", headers=headers_b)
    assert r_anal.status_code == 403, f"Cross-brand analytics access must return 403, got {r_anal.status_code}"

    cases_res = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {tokens['admin']}"})
    cases = cases_res.json()
    if cases:
        amul_case = cases[0]
        r_case_view = client.get(f"/api/v1/cases/{amul_case['id']}", headers=headers_b)
        assert r_case_view.status_code == 403, f"Cross-brand case detail access must return 403, got {r_case_view.status_code}"

        r_case_rev = client.post(
            f"/api/v1/cases/{amul_case['id']}/review",
            json={"new_status": "REJECTED", "comments": "Unauthorized review from competitor"},
            headers=headers_b
        )
        assert r_case_rev.status_code == 403, f"Cross-brand case review must return 403, got {r_case_rev.status_code}"

    prods = client.get("/api/v1/products").json()
    amul_gold = next((p for p in prods if "gold" in p["name"].lower()), None)
    if amul_gold:
        r_add_var = client.post(
            f"/api/v1/products/{amul_gold['id']}/variants",
            json={"variant_name": "Injected Competitor Variant", "fat_content": "10%"},
            headers=headers_b
        )
        assert r_add_var.status_code == 403, f"Cross-brand variant injection must return 403, got {r_add_var.status_code}"

        amul_brand_id = amul_gold.get("brand_id")
        if amul_brand_id:
            r_spoof_prod = client.post(
                "/api/v1/products",
                json={"brand_id": amul_brand_id, "name": "Fake Spoofed Product", "category": "MILK", "variants": []},
                headers=headers_b
            )
            assert r_spoof_prod.status_code == 403, f"Creating product under another brand must return 403, got {r_spoof_prod.status_code}"

def test_upload_redteam_empty_file():
    empty_bytes = b""
    res = client.post(
        "/api/v1/scans/upload",
        data={"view_type": "FRONT"},
        files={"file": ("empty.jpg", io.BytesIO(empty_bytes), "image/jpeg")}
    )
    assert res.status_code == 400
    assert "empty" in res.json().get("detail", "").lower()

def test_upload_redteam_executable_disguised_as_jpeg():
    exe_payload = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00This program cannot be run in DOS mode."
    res = client.post(
        "/api/v1/scans/upload",
        data={"view_type": "FRONT"},
        files={"file": ("malware.exe.jpg", io.BytesIO(exe_payload), "image/jpeg")}
    )
    assert res.status_code in (400, 415), f"Executable upload must be rejected, got {res.status_code}"

def test_upload_redteam_php_script_disguised_as_png():
    php_payload = b"<?php echo 'malicious backdoor'; phpinfo(); ?>"
    res = client.post(
        "/api/v1/scans/upload",
        data={"view_type": "FRONT"},
        files={"file": ("shell.png", io.BytesIO(php_payload), "image/png")}
    )
    assert res.status_code in (400, 415), f"PHP script must be rejected, got {res.status_code}"

def test_upload_redteam_svg_xss_disguised():
    svg_payload = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(document.cookie)</script></svg>"
    res = client.post(
        "/api/v1/scans/upload",
        data={"view_type": "FRONT"},
        files={"file": ("xss.jpg", io.BytesIO(svg_payload), "image/jpeg")}
    )
    assert res.status_code in (400, 415), f"SVG script injection must be rejected, got {res.status_code}"

def test_liveness_and_readiness_probes():
    r_live = client.get("/liveness")
    assert r_live.status_code == 200
    assert r_live.json().get("status") == "alive"

    r_ready = client.get("/readiness")
    assert r_ready.status_code == 200
    data = r_ready.json()
    assert data.get("status") == "ready"
    assert data["checks"]["database"] == "connected"
    assert data["checks"]["storage"] == "read_write_verified"

def test_request_id_correlation_header():
    custom_id = "test-corr-" + str(uuid.uuid4())
    res = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_id

    res2 = client.get("/health")
    assert "X-Request-ID" in res2.headers
    assert len(res2.headers["X-Request-ID"]) >= 16
