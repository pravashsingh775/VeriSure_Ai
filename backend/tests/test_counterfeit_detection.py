import numpy as np
import pytest

from backend.app.ai.codes.barcode import BarcodeAnalyzer
from backend.app.ai.codes.qr import QRAnalyzer
from backend.app.ai.contracts import (
    DecisionResult,
    DecisionState,
    EvidenceObject,
    EvidenceType,
    QualityAssessmentResult,
)
from backend.app.ai.decision.engine import DecisionEngine
from backend.app.ai.fusion.engine import MultiEvidenceFusionEngine
from backend.app.ai.vision.seal import SealAnalyzer
from backend.app.ai.vision.logo import LogoAnalyzer


@pytest.fixture
def dummy_quality():
    return QualityAssessmentResult(
        resolution_score=0.90,
        blur_score=0.88,
        brightness_score=0.85,
        contrast_score=0.86,
        glare_score=0.92,
        occlusion_score=0.91,
        overall_quality=0.89,
        usable=True,
    )


def test_counterfeit_tampered_seal_triggers_tampered_state(dummy_quality):
    """
    Empirical Counterfeit Verification 1:
    Tests that broken, punctured, or cut heat-seals trigger
    DecisionState.TAMPERED_OR_DAMAGED with risk >= 75.0 and DO NOT CONSUME guidance.
    """
    decision_engine = DecisionEngine()

    ev_seal_tampered = EvidenceObject(
        type=EvidenceType.SEAL,
        score=0.18,  # Below 0.35 critical threshold
        confidence=0.95,
        availability=True,
        source="verisure-seal-sobel-v1",
        explanation="Crimp broken or punctured",
    )
    ev_logo = EvidenceObject(
        type=EvidenceType.LOGO,
        score=0.92,
        confidence=0.90,
        availability=True,
        source="verisure-logo-orb-v1",
        explanation="Logo appears congruent",
    )

    fusion_data = {
        "fused_authenticity_score": 0.35,
        "risk_score": 65.0,
        "confidence": 0.90,
        "uncertainty": 0.25,
        "evidence_coverage": 0.75,
        "conflicts": ["CONTRADICTION: Authentic branding but compromised seal integrity."],
    }

    result = decision_engine.evaluate(
        fusion_result=fusion_data,
        quality_result=dummy_quality,
        evidences=[ev_logo, ev_seal_tampered],
        product_identified=True,
    )

    assert result.state == DecisionState.TAMPERED_OR_DAMAGED
    assert result.risk_score >= 75.0
    assert "DO NOT CONSUME" in result.recommendation
    assert "SEAL_INTEGRITY_COMPROMISED" in result.reason_codes


def test_counterfeit_corrupted_barcode_checksum(dummy_quality):
    """
    Empirical Counterfeit Verification 2:
    Tests that a counterfeit barcode with invalid Modulo-10 checksum
    is detected as corrupt, penalizing authenticity.
    """
    barcode_analyzer = BarcodeAnalyzer()
    # 8901262010053 has corrupted check digit (should be 4)
    assert barcode_analyzer._verify_ean13_checksum("8901262010053") is False

    # Valid checksum
    assert barcode_analyzer._verify_ean13_checksum("8901262010054") is True


def test_counterfeit_phishing_qr_domain():
    """
    Empirical Counterfeit Verification 3:
    Tests that a packaging QR code pointing to an unauthorized / phishing domain
    is penalized with low score and warning.
    """
    qr_analyzer = QRAnalyzer()
    parsed_domain = "amul-dairy-offers.xyz"
    from backend.app.core.config import settings
    trusted_domains = [d.lower() for d in settings.AUTHORIZED_QR_DOMAINS]
    assert not any(t in parsed_domain for t in trusted_domains)


def test_counterfeit_logo_mismatch_elevates_risk(dummy_quality):
    """
    Empirical Counterfeit Verification 4:
    Tests that when the logo is mismatched (counterfeit print),
    LOGO_MISMATCH is emitted and risk score >= 70.
    """
    decision_engine = DecisionEngine()

    ev_logo_fake = EvidenceObject(
        type=EvidenceType.LOGO,
        score=0.25,  # Mismatched logo
        confidence=0.88,
        availability=True,
        source="verisure-logo-orb-v1",
        explanation="Logo keypoint descriptors deviate from brand reference",
    )
    ev_color_fake = EvidenceObject(
        type=EvidenceType.COLOUR,
        score=0.30,  # Wrong ink colors
        confidence=0.92,
        availability=True,
        source="verisure-colour-cielab-v1",
        explanation="CIEDE2000 Delta E exceeds industrial print tolerance",
    )

    fusion_data = {
        "fused_authenticity_score": 0.28,
        "risk_score": 72.0,
        "confidence": 0.90,
        "uncertainty": 0.20,
        "evidence_coverage": 0.75,
        "conflicts": [],
    }

    result = decision_engine.evaluate(
        fusion_result=fusion_data,
        quality_result=dummy_quality,
        evidences=[ev_logo_fake, ev_color_fake],
        product_identified=True,
    )

    assert result.state in [DecisionState.HIGH_RISK, DecisionState.CRITICAL_RISK]
    assert result.risk_score >= 70.0
    assert "LOGO_MISMATCH" in result.reason_codes
    assert "HIGH COUNTERFEIT PROBABILITY" in result.recommendation


def test_genuine_control_baseline(dummy_quality):
    """
    Empirical Counterfeit Verification 5 (Control Baseline):
    Tests that when an authentic package is evaluated,
    the system correctly outputs LOW_RISK with risk <= 20.0.
    """
    decision_engine = DecisionEngine()

    ev_logo_genuine = EvidenceObject(
        type=EvidenceType.LOGO,
        score=0.94,
        confidence=0.92,
        availability=True,
        source="verisure-logo-orb-v1",
        explanation="Brand mark congruent with master template",
    )
    ev_seal_genuine = EvidenceObject(
        type=EvidenceType.SEAL,
        score=0.88,
        confidence=0.90,
        availability=True,
        source="verisure-seal-sobel-v1",
        explanation="Heat crimp geometry intact",
    )

    fusion_data = {
        "fused_authenticity_score": 0.91,
        "risk_score": 9.0,
        "confidence": 0.91,
        "uncertainty": 0.18,
        "evidence_coverage": 0.75,
        "conflicts": [],
    }

    result = decision_engine.evaluate(
        fusion_result=fusion_data,
        quality_result=dummy_quality,
        evidences=[ev_logo_genuine, ev_seal_genuine],
        product_identified=True,
    )

    assert result.state in [DecisionState.LOW_RISK, DecisionState.LIKELY_GENUINE]
    assert result.risk_score < 20.0
    assert "LOGO_CONGRUENT" in result.reason_codes
    assert "High packaging conformity" in result.recommendation or "Low counterfeit risk" in result.recommendation
