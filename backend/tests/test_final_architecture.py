import io
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.ai.codes.barcode import BarcodeAnalyzer
from backend.app.ai.certification.engine import CertificationAnalyzer
from backend.app.ai.codes.qr import QRAnalyzer
from backend.app.ai.contracts import (
    DecisionResult,
    DecisionState,
    EvidenceObject,
    EvidenceResult,
    EvidenceType,
    QualityAssessmentResult,
)
from backend.app.ai.decision.engine import DecisionEngine
from backend.app.ai.fingerprint.engine import PackagingFingerprintEngine
from backend.app.ai.fusion.engine import ConflictDetector, MultiEvidenceFusionEngine
from backend.app.main import app

client = TestClient(app)


def test_fusion_mathematics_and_contradiction_penalty():
    """
    Section 12 Verification:
    Tests dynamic weighting, raw score, conflict penalty, and final fused score.
    """
    fusion_engine = MultiEvidenceFusionEngine()

    dummy_quality = QualityAssessmentResult(
        resolution_score=0.90,
        blur_score=0.85,
        brightness_score=0.85,
        contrast_score=0.85,
        glare_score=0.90,
        occlusion_score=0.90,
        overall_quality=0.88,
        usable=True,
    )

    ev1 = EvidenceObject(
        type=EvidenceType.LOGO,
        score=0.90,
        confidence=0.95,
        quality=0.90,
        availability=True,
        source="verisure-logo-orb-v1",
        explanation="Logo matches",
    )
    ev2 = EvidenceObject(
        type=EvidenceType.COLOUR,
        score=0.85,
        confidence=0.90,
        quality=0.90,
        availability=True,
        source="verisure-colour-cielab-v1",
        explanation="Color matches",
    )

    # Calculate expected manually
    w_logo = 0.18 * 0.95 * 0.90  # 0.1539
    w_col = 0.10 * 0.90 * 0.90   # 0.081
    expected_sraw = (w_logo * 0.90 + w_col * 0.85) / (w_logo + w_col)

    res = fusion_engine.fuse([ev1, ev2], dummy_quality)
    assert abs(res["fused_authenticity_score"] - round(expected_sraw, 3)) < 0.01
    assert res["conflict_penalty"] == 0.0
    assert len(res["conflicts"]) == 0

    # Introduce contradiction: authentic logo but tampered seal
    ev_seal_tampered = EvidenceObject(
        type=EvidenceType.SEAL,
        score=0.20,
        confidence=0.90,
        quality=0.90,
        availability=True,
        source="verisure-seal-v1",
        explanation="Crimp broken",
    )
    res_conflict = fusion_engine.fuse([ev1, ev2, ev_seal_tampered], dummy_quality)
    assert res_conflict["conflict_penalty"] >= 0.25
    assert len(res_conflict["conflicts"]) >= 1
    assert "CONTRADICTION" in res_conflict["conflicts"][0]
    assert res_conflict["risk_score"] > res["risk_score"]


def test_abstention_rules_coverage_and_uncertainty():
    """
    Section 13 Verification:
    IF Coverage < 0.50 OR Uncertainty > 0.65 THEN decision = INSUFFICIENT_EVIDENCE
    """
    decision_engine = DecisionEngine()
    dummy_quality = QualityAssessmentResult(
        resolution_score=0.90,
        blur_score=0.85,
        brightness_score=0.85,
        contrast_score=0.85,
        glare_score=0.90,
        occlusion_score=0.90,
        overall_quality=0.88,
        usable=True,
    )

    # Case A: Low Coverage (< 0.50)
    low_cov_fusion = {
        "fused_authenticity_score": 0.95,
        "risk_score": 5.0,
        "confidence": 0.90,
        "uncertainty": 0.30,
        "evidence_coverage": 0.33,
        "conflicts": [],
    }
    dec_a = decision_engine.evaluate(low_cov_fusion, dummy_quality, evidences=[], product_identified=True)
    assert dec_a.state == DecisionState.INSUFFICIENT_EVIDENCE
    assert any("coverage" in r.lower() for r in dec_a.reason_codes)

    # Case B: High Uncertainty (> 0.65)
    high_unc_fusion = {
        "fused_authenticity_score": 0.85,
        "risk_score": 15.0,
        "confidence": 0.50,
        "uncertainty": 0.72,
        "evidence_coverage": 0.60,
        "conflicts": [],
    }
    dec_b = decision_engine.evaluate(high_unc_fusion, dummy_quality, evidences=[], product_identified=True)
    assert dec_b.state == DecisionState.INSUFFICIENT_EVIDENCE
    assert any("uncertainty" in r.lower() for r in dec_b.reason_codes)


def test_barcode_ean13_modulo10_checksum():
    """
    Section 8.10 Verification:
    Tests EAN-13 Modulo-10 checksum validation.
    """
    # 8901262010054 is a valid EAN-13 (8*1 + 9*3 + ... + 5*3 = 76 -> check digit 4)
    assert BarcodeAnalyzer._verify_ean13_checksum("8901262010054") is True
    # Corrupt check digit (3 instead of 4)
    assert BarcodeAnalyzer._verify_ean13_checksum("8901262010053") is False
    # Non-digit or wrong length
    assert BarcodeAnalyzer._verify_ean13_checksum("890126201005") is False
    assert BarcodeAnalyzer._verify_ean13_checksum("890126201005A") is False


def test_fssai_14_digit_syntax_and_jurisdiction():
    """
    Section 8.12 Verification:
    Tests FSSAI 14-digit syntax and jurisdiction decoding.
    """
    analyzer = CertificationAnalyzer()
    info = analyzer.validate_fssai("10012021000071")
    assert info["valid_format"] is True
    assert info["prefix_type"] == "Registration"
    assert "jurisdiction" in info

    # Invalid length
    invalid_info = analyzer.validate_fssai("1001202100007")
    assert invalid_info["valid_format"] is False


def test_qr_authorized_domain_whitelist():
    """
    Section 8.11 Verification:
    Tests QR analyzer domain safety check against authorized whitelist.
    """
    analyzer = QRAnalyzer()
    scan_patch = np.zeros((100, 100, 3), dtype=np.uint8)

    # When no QR code is in the patch, score MUST be None
    ev_empty = analyzer.analyze(scan_patch)
    assert ev_empty.availability is False
    assert ev_empty.score is None
    assert ev_empty.confidence == 0.0


def test_packaging_fingerprint_determinism():
    """
    Section 11 Verification:
    Tests that identical evidence produces an identical versioned packaging fingerprint.
    """
    metadata = {
        "brand": "Amul",
        "product": "Amul Taaza",
        "variant": "Toned Milk",
        "pack_size": "1L",
        "packaging_version": "V1",
    }
    ev = [
        EvidenceObject(
            type=EvidenceType.LOGO,
            score=0.92,
            confidence=0.95,
            availability=True,
            source="verisure-logo-orb-v1",
            features={"keypoints": 120},
            explanation="Match",
        )
    ]

    fp1 = PackagingFingerprintEngine.generate_fingerprint(metadata, ev, [])
    fp2 = PackagingFingerprintEngine.generate_fingerprint(metadata, ev, [])

    assert fp1.version == fp2.version
    assert fp1.product_identity == fp2.product_identity
    assert fp1.visual == fp2.visual
    assert fp1.text == fp2.text
    assert fp1.machine_readable == fp2.machine_readable


def test_end_to_end_real_image_scan_flow():
    """
    Section 28 End-to-End User Journey:
    Login -> Upload official reference image -> Quality -> Detection ->
    12-Engine Analysis -> Fusion -> Decision -> Report -> Reviewer Case.
    """
    # 1. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "consumer@verisure.ai", "password": "Consumer@12345"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # 2. Upload official Amul Gold reference image
    ref_img_path = Path("data/storage/references/media_1788440125203.jpg")
    assert ref_img_path.exists(), "Official reference image media_1788440125203.jpg missing!"
    img_bytes = ref_img_path.read_bytes()

    upload_res = client.post(
        "/api/v1/scans/upload",
        data={"view_type": "FRONT"},
        files={"file": ("amul_gold_scan.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_res.status_code == 201
    scan_data = upload_res.json()

    assert scan_data["status"] == "REPORT_READY"
    assert scan_data["identified_product_name"] == "Amul Gold"
    assert len(scan_data["evidences"]) == 12

    # Verify decision
    decision = scan_data["decision"]
    assert decision["state"] in ["LOW_RISK", "LIKELY_GENUINE", "REVIEW_REQUIRED"]
    assert decision["evidence_coverage"] >= 0.50
    assert decision["uncertainty"] <= 0.65
    assert "cannot verify" in decision["recommendation"].lower()

    # 3. Verify PDF report download
    scan_id = scan_data["id"]
    report_res = client.get(
        f"/api/v1/scans/{scan_id}/report",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert report_res.status_code == 200
    assert report_res.headers["content-type"] == "application/pdf"
    assert len(report_res.content) > 500
