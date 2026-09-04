import asyncio
import io
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app.ai.contracts import DecisionResult, DecisionState, EvidenceObject, EvidenceType, QualityAssessmentResult
from backend.app.ai.decision.engine import DecisionEngine
from backend.app.ai.ocr.engine import OCREngine
from backend.app.ai.quality.engine import ImageQualityEngine
from backend.app.ai.retrieval.engine import ReferenceRetriever
from backend.app.ai.vision.colour import ColourAnalyzer
from backend.app.ai.vision.layout import LayoutAnalyzer
from backend.app.ai.vision.logo import LogoAnalyzer
from backend.app.ai.vision.shape import ShapeAnalyzer
from backend.app.ai.vision.texture import TextureAnalyzer
from backend.app.main import app
from backend.tests.helpers import create_test_amul_image, get_image_bytes

client = TestClient(app)


def test_quality_engine_sharp_vs_blurry():
    quality_engine = ImageQualityEngine()

    sharp_img = create_test_amul_image(blur=False)
    sharp_res = quality_engine.assess(sharp_img)
    assert sharp_res.usable is True
    assert sharp_res.blur_score > 0.60
    assert sharp_res.overall_quality >= 0.70

    blurry_img = create_test_amul_image(blur=True)
    blurry_res = quality_engine.assess(blurry_img)
    assert blurry_res.usable is False
    assert blurry_res.blur_score < 0.35
    assert "HIGH_MOTION_BLUR" in blurry_res.reasons
    assert "focus" in blurry_res.guidance.lower()


def test_consumer_scan_genuine_amul_taaza():
    # Login as consumer
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "consumer@verisure.ai", "password": "Consumer@12345"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Generate test image
    img_bgr = create_test_amul_image()
    img_bytes = get_image_bytes(img_bgr)

    upload_res = client.post(
        "/api/v1/scans/upload",
        data={"view_type": "FRONT"},
        files={"file": ("amul_taaza_front.png", io.BytesIO(img_bytes), "image/png")},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert upload_res.status_code == 201
    data = upload_res.json()

    assert data["status"] == "REPORT_READY"
    assert data["identified_product_name"] == "Amul Taaza"
    assert data["packaging_version_code"] == "V1"
    assert len(data["evidences"]) == 12  # All 12 evidence engines returned

    # Verify decision state and calibrated language
    decision = data["decision"]
    assert decision["state"] in ["LIKELY_GENUINE", "LOW_RISK", "MEDIUM_RISK"]
    assert "Safe for standard consumption" not in decision["recommendation"]
    assert "cannot verify" in decision["recommendation"]
    assert decision["risk_score"] < 40.0
    assert decision["confidence"] >= 0.60
    assert decision["evidence_coverage"] >= 0.30

    # Verify that reference-dependent engines report valid evidence objects
    for ev in data["evidences"]:
        assert "type" in ev
        assert "confidence" in ev
        assert "explanation" in ev
        if ev["availability"]:
            assert ev["score"] is not None
            assert 0.0 <= ev["score"] <= 1.0

    # Verify fingerprint
    assert data["fingerprint"] is not None
    assert data["fingerprint"]["product_identity"]["product"] == "Amul Taaza"

    # Verify PDF Report download
    scan_id = data["id"]
    report_res = client.get(
        f"/api/v1/scans/{scan_id}/report",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert report_res.status_code == 200
    assert report_res.headers["content-type"] == "application/pdf"
    assert len(report_res.content) > 1000

    # Verify Scan History
    history_res = client.get(
        "/api/v1/scans/history/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) >= 1
    assert any(h["id"] == scan_id for h in history)


def test_tampered_seal_detection():
    # Tampered crimp band image
    img_bgr = create_test_amul_image(tamper_seal=True)
    img_bytes = get_image_bytes(img_bgr)

    upload_res = client.post(
        "/api/v1/scans/upload",
        data={"view_type": "FRONT"},
        files={"file": ("tampered_milk.png", io.BytesIO(img_bytes), "image/png")}
    )
    assert upload_res.status_code == 201
    data = upload_res.json()

    decision = data["decision"]
    assert decision["state"] == "TAMPERED_OR_DAMAGED"
    assert decision["risk_score"] >= 70.0
    assert "DO NOT CONSUME" in decision["recommendation"]
    assert "SEAL_INTEGRITY_COMPROMISED" in decision["reason_codes"]
    assert data["suspicious_case_id"] is not None  # Auto-triaged suspicious case


def test_blurry_scan_triggers_insufficient_evidence():
    # Blurry image
    img_bgr = create_test_amul_image(blur=True)
    img_bytes = get_image_bytes(img_bgr)

    upload_res = client.post(
        "/api/v1/scans/upload",
        data={"view_type": "FRONT"},
        files={"file": ("blurry_scan.png", io.BytesIO(img_bytes), "image/png")}
    )
    assert upload_res.status_code == 201
    data = upload_res.json()

    decision = data["decision"]
    assert decision["state"] == "INSUFFICIENT_EVIDENCE"
    assert "IMAGE_QUALITY_INSUFFICIENT" in decision["reason_codes"]
    assert "steady" in decision["recommendation"].lower() or "focus" in decision["recommendation"].lower()


# =========================================================================
# FORENSIC AUDIT REMEDIATION TESTS
# =========================================================================

def test_missing_reference_crop_returns_unavailable_without_fabrication():
    """
    PRIORITY 1 & 4 VERIFICATION:
    Verifies that when trusted reference crop is unavailable:
    LogoAnalyzer, ColourAnalyzer, LayoutAnalyzer, ShapeAnalyzer, TextureAnalyzer
    honestly report availability=False, score=None, confidence=0.0, and
    explanation='Trusted reference unavailable for comparison.'
    """
    scan_crop = np.zeros((300, 300, 3), dtype=np.uint8)
    scan_crop[50:150, 50:150] = [200, 150, 50]  # Non-trivial patch

    analyzers = [
        (LogoAnalyzer(), EvidenceType.LOGO),
        (ColourAnalyzer(), EvidenceType.COLOUR),
        (LayoutAnalyzer(), EvidenceType.LAYOUT),
        (ShapeAnalyzer(), EvidenceType.SHAPE),
        (TextureAnalyzer(), EvidenceType.TEXTURE),
    ]

    for analyzer, expected_type in analyzers:
        ev: EvidenceObject = analyzer.analyze(scan_crop_bgr=scan_crop, reference_crop_bgr=None)
        assert ev.type == expected_type
        assert ev.availability is False
        assert ev.score is None
        assert ev.confidence == 0.0
        assert "Trusted reference unavailable" in ev.explanation
        assert "TRUSTED_REFERENCE_UNAVAILABLE" in ev.warnings


def test_missing_ocr_text_returns_unavailable_without_fabrication():
    """
    PRIORITY 1 VERIFICATION:
    Verifies that when OCR text is empty or model cannot read text,
    it returns availability=False, score=None, confidence=0.0,
    and NEVER returns a fabricated Amul fallback string.
    """
    ocr_engine = OCREngine()
    blank_crop = np.zeros((200, 200, 3), dtype=np.uint8)

    ev: EvidenceObject = ocr_engine.analyze(scan_crop_bgr=blank_crop)
    assert ev.type == EvidenceType.OCR
    assert ev.availability is False
    assert ev.score is None
    assert ev.confidence == 0.0
    assert "No readable text tokens detected" in ev.explanation
    # Ensure hard-coded fallback string is completely eradicated
    assert "AMUL TAAZA HOMOGENISED TONED MILK" not in ev.features.get("raw_text", "")


def test_decision_engine_language_no_consumption_claim():
    """
    PRIORITY 6 VERIFICATION:
    Ensures 'Safe for standard consumption' is completely removed and replaced
    by honest packaging risk assessment disclaimers.
    """
    engine = DecisionEngine()
    dummy_quality = QualityAssessmentResult(
        resolution_score=0.90,
        blur_score=0.85,
        brightness_score=0.88,
        contrast_score=0.85,
        glare_score=0.90,
        occlusion_score=0.95,
        overall_quality=0.90,
        usable=True,
        reasons=[],
        guidance="Clear"
    )

    # Test LOW_RISK decision
    low_risk_fusion = {
        "fused_authenticity_score": 0.85,
        "risk_score": 15.0,
        "confidence": 0.85,
        "uncertainty": 0.20,
        "evidence_coverage": 0.70,
        "conflicts": []
    }
    dec_low = engine.evaluate(low_risk_fusion, dummy_quality, evidences=[], product_identified=True)
    assert dec_low.state == DecisionState.LOW_RISK
    assert "Safe for standard consumption" not in dec_low.recommendation
    assert "cannot verify the chemical, biological, or internal contents" in dec_low.recommendation

    # Test LIKELY_GENUINE decision
    likely_genuine_fusion = {
        "fused_authenticity_score": 0.95,
        "risk_score": 5.0,
        "confidence": 0.92,
        "uncertainty": 0.10,
        "evidence_coverage": 0.85,
        "conflicts": []
    }
    dec_gen = engine.evaluate(likely_genuine_fusion, dummy_quality, evidences=[], product_identified=True)
    assert dec_gen.state == DecisionState.LIKELY_GENUINE
    assert "Safe for standard consumption" not in dec_gen.recommendation
    assert "cannot verify internal biological or chemical contents" in dec_gen.recommendation


def test_historical_packaging_retrieval_supported():
    """
    PRIORITY 5 VERIFICATION:
    Verifies that ReferenceRetriever does not discard DEPRECATED packaging versions
    and flags is_historical=True.
    """
    from sqlalchemy import select
    from backend.app.core.database import AsyncSessionLocal
    from backend.app.models.brand import Brand
    from backend.app.models.packaging import PackagingVersion
    from backend.app.models.product import Product, ProductPackSize, ProductVariant

    async def _run():
        async with AsyncSessionLocal() as db:
            # Create a historical packaging version under Amul brand
            brand = (await db.execute(select(Brand).where(Brand.code == "AMUL"))).scalar_one()
            prod = Product(name="Amul Historical Milk", brand_id=brand.id)
            db.add(prod)
            await db.flush()

            var = ProductVariant(product_id=prod.id, variant_name="Historical Variant")
            db.add(var)
            await db.flush()

            ps = ProductPackSize(variant_id=var.id, pack_size="500ml")
            db.add(ps)
            await db.flush()

            hist_pv = PackagingVersion(
                pack_size_id=ps.id,
                version_code="V_OLD",
                status="DEPRECATED",
                expected_barcode="8901234000999"
            )
            db.add(hist_pv)
            await db.commit()

            # Retrieve candidate with historical barcode
            candidates = await ReferenceRetriever.retrieve_candidates(
                db=db,
                detected_text="Amul Historical Milk",
                detected_barcode="8901234000999"
            )

            hist_candidates = [c for c in candidates if c["version_code"] == "V_OLD"]
            assert len(hist_candidates) >= 1
            assert hist_candidates[0]["packaging_version_status"] == "DEPRECATED"
            assert hist_candidates[0]["is_historical"] is True
            assert hist_candidates[0]["retrieval_score"] > 0.80

            # Teardown test historical records to preserve locked 3-product scope
            await db.delete(hist_pv)
            await db.delete(ps)
            await db.delete(var)
            await db.delete(prod)
            await db.commit()

    asyncio.run(_run())


def test_regression_no_hardcoded_evidence_fallbacks():
    """
    REGRESSION TEST:
    Ensures that no production AI engine returns hardcoded placeholder similarity
    values when uncompared or when reference templates are omitted.
    """
    from backend.app.ai.fusion.engine import MultiEvidenceFusionEngine

    # 1. Vision Analyzers without reference must never emit old hardcoded values (0.85, 0.92, 0.90, 0.93, 0.89)
    synthetic_patch = np.full((250, 250, 3), 128, dtype=np.uint8)
    cv2.circle(synthetic_patch, (125, 125), 50, (255, 0, 0), -1)

    logo_ev = LogoAnalyzer().analyze(synthetic_patch, reference_crop_bgr=None)
    colour_ev = ColourAnalyzer().analyze(synthetic_patch, reference_crop_bgr=None)
    layout_ev = LayoutAnalyzer().analyze(synthetic_patch, reference_crop_bgr=None)
    shape_ev = ShapeAnalyzer().analyze(synthetic_patch, reference_crop_bgr=None)
    texture_ev = TextureAnalyzer().analyze(synthetic_patch, reference_crop_bgr=None)

    for ev in [logo_ev, colour_ev, layout_ev, shape_ev, texture_ev]:
        assert ev.score is None
        assert ev.confidence == 0.0
        assert ev.availability is False
        assert ev.score not in [0.85, 0.92, 0.90, 0.93, 0.89]

    # 2. Multi-Evidence Fusion with uncompared vision engines must calculate weights only on available engines
    fusion_engine = MultiEvidenceFusionEngine()
    quality = QualityAssessmentResult(
        resolution_score=0.90, blur_score=0.85, brightness_score=0.88,
        contrast_score=0.85, glare_score=0.90, occlusion_score=0.95,
        overall_quality=0.90, usable=True, reasons=[], guidance="Clear"
    )

    fused = fusion_engine.fuse([logo_ev, colour_ev, layout_ev, shape_ev, texture_ev], quality)
    # Since none of these 5 engines are available, coverage must be 0.0, uncertainty high
    assert fused["evidence_coverage"] == 0.0
    assert fused["uncertainty"] >= 0.90
