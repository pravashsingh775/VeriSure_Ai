import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def get_admin_token():
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@verisure.ai", "password": "Admin@12345"}
    )
    return login_res.json()["access_token"]


def get_brand_admin_token():
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "amul_admin@verisure.ai", "password": "Amul@12345"}
    )
    return login_res.json()["access_token"]


def test_suspicious_cases_and_reviews():
    admin_token = get_admin_token()

    # 1. List cases
    cases_res = client.get(
        "/api/v1/cases",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert cases_res.status_code == 200
    cases = cases_res.json()
    if not cases:
        import io
        from backend.tests.helpers import create_test_amul_image, get_image_bytes
        img_bgr = create_test_amul_image(tamper_seal=True)
        img_bytes = get_image_bytes(img_bgr)
        client.post(
            "/api/v1/scans/upload",
            data={"view_type": "FRONT"},
            files={"file": ("tamper.png", io.BytesIO(img_bytes), "image/png")}
        )
        cases_res = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {admin_token}"})
        cases = cases_res.json()

    assert len(cases) >= 1
    case = cases[0]
    assert "case_number" in case

    # 2. Add review transition
    review_res = client.post(
        f"/api/v1/cases/{case['id']}/review",
        json={
            "new_status": "VERIFIED_SUSPICIOUS",
            "comments": "Confirmed heat-seal crimp mismatch and suspect packaging substrate in physical lab review."
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert review_res.status_code == 200
    updated_case = review_res.json()
    assert updated_case["status"] == "VERIFIED_SUSPICIOUS"
    assert len(updated_case["reviews"]) >= 1


def test_feedback_and_curated_learning():
    admin_token = get_admin_token()

    fb_res = client.post(
        "/api/v1/feedback",
        json={
            "verified_label": "COUNTERFEIT_SUSPICIOUS",
            "dataset_category": "VERIFIED_SUSPICIOUS",
            "notes": "Verified packaging replica missing micro-embossed seal pattern."
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert fb_res.status_code == 201
    fb_data = fb_res.json()
    assert fb_data["verified_label"] == "COUNTERFEIT_SUSPICIOUS"

    list_fb = client.get(
        "/api/v1/feedback",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert list_fb.status_code == 200
    assert len(list_fb.json()) >= 1


def test_datasets_and_versioning():
    admin_token = get_admin_token()
    unique_tag = uuid.uuid4().hex[:6]

    # 1. Create dataset
    ds_res = client.post(
        "/api/v1/datasets",
        json={
            "name": f"Amul Packaging Integrity Benchmark {unique_tag}",
            "description": "Curated dataset split by physical container batch",
            "domain_tag": "AMUL_MILK"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert ds_res.status_code == 201
    dataset = ds_res.json()

    # 2. Create snapshot version with leakage-free splits
    ver_res = client.post(
        f"/api/v1/datasets/{dataset['id']}/versions",
        json={
            "version_tag": "v1.0.0",
            "split_strategy": "PACKAGE_AND_SESSION_ISOLATED",
            "metadata_json": {"collection_year": 2026},
            "samples": [
                {"image_path": "data/sample_001.png", "label": "GENUINE", "split": "TRAIN", "package_id": "pkg_01"},
                {"image_path": "data/sample_002.png", "label": "GENUINE", "split": "VAL", "package_id": "pkg_02"},
                {"image_path": "data/sample_003.png", "label": "SUSPICIOUS", "split": "TEST", "package_id": "pkg_03"}
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert ver_res.status_code == 201
    version = ver_res.json()
    assert version["train_count"] == 1
    assert version["val_count"] == 1
    assert version["test_count"] == 1
    assert version["is_locked"] is True


def test_models_registry_and_evaluation():
    admin_token = get_admin_token()

    # 1. List models
    models_res = client.get(
        "/api/v1/models",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert models_res.status_code == 200
    models = models_res.json()
    assert len(models) >= 2

    fusion_model = next(m for m in models if "Fusion" in m["name"])
    assert len(fusion_model["versions"]) >= 1
    active_version = fusion_model["versions"][0]

    # 2. Trigger real scientific evaluation run
    eval_res = client.post(
        f"/api/v1/models/versions/{active_version['id']}/evaluate",
        json={"simulate_perturbations": True},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["accuracy"] is None
    assert eval_data["f1"] is None
    assert eval_data["confusion_matrix"]["status"] == "EMPIRICAL_DATASET_NOT_YET_AVAILABLE"
    assert "Empirical dataset not yet available" in eval_data["confusion_matrix"]["message"]


def test_analytics_and_audit_logs():
    admin_token = get_admin_token()
    brand_token = get_brand_admin_token()

    # 1. Admin analytics
    admin_analytics = client.get(
        "/api/v1/analytics/admin",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_analytics.status_code == 200
    a_data = admin_analytics.json()
    assert a_data["total_scans"] >= 1
    assert a_data["quality_pass_rate_percent"] > 0

    # 2. Brand analytics
    brands_res = client.get("/api/v1/brands")
    amul_id = next(b["id"] for b in brands_res.json() if b["code"] == "AMUL")

    brand_analytics = client.get(
        f"/api/v1/analytics/brand/{amul_id}",
        headers={"Authorization": f"Bearer {brand_token}"}
    )
    assert brand_analytics.status_code == 200
    b_data = brand_analytics.json()
    assert b_data["brand_code"] == "AMUL"
    assert b_data["active_packaging_versions"] >= 3

    # 3. Audit logs query
    audit_res = client.get(
        "/api/v1/audit?limit=20",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 1
    assert any("changes" in log for log in logs)

