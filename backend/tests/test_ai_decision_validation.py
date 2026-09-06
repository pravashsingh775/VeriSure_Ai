"""
VeriSure AI — AI Decision Correctness & Red-Team Master Regression Test Suite
Validates mathematical fusion boundaries, monotonicity, fault-isolation barriers,
abstention gatekeepers, seal tamper triggers, competitor rejection, duplicate views,
and deterministic decision reproducibility.
"""
import numpy as np
import pytest

from backend.app.ai.contracts import (
    DecisionState,
    EvidenceObject,
    EvidenceType,
    QualityAssessmentResult,
)
from backend.app.ai.decision.engine import DecisionEngine
from backend.app.ai.fusion.engine import MultiEvidenceFusionEngine
from backend.app.ai.orchestrator import AIOrchestrator


@pytest.fixture
def dummy_high_quality():
    return QualityAssessmentResult(
        resolution_score=0.95,
        blur_score=0.92,
        brightness_score=0.90,
        contrast_score=0.91,
        glare_score=0.94,
        occlusion_score=0.95,
        overall_quality=0.93,
        usable=True,
    )


# ---------------------------------------------------------------------------
# 1. Mathematical Bounds & NaN Guards
# ---------------------------------------------------------------------------
def test_fusion_mathematical_bounds_empty_and_nan(dummy_high_quality):
    """
    Tests that empty evidence lists, NaN scores, and zero weights are safely handled
    without division by zero, staying strictly within mathematical bounds.
    """
    engine = MultiEvidenceFusionEngine()

    # Case A: Empty evidence list
    res_empty = engine.fuse([], dummy_high_quality)
    assert res_empty["fused_authenticity_score"] == 0.50
    assert res_empty["risk_score"] == 50.0
    assert res_empty["evidence_coverage"] == 0.0
    assert 0.05 <= res_empty["uncertainty"] <= 0.95

    # Case B: Evidence with None / unavailable score
    ev_none = EvidenceObject(
        type=EvidenceType.LOGO,
        score=None,
        confidence=0.90,
        quality=0.85,
        availability=False,
        source="test-none",
        explanation="None score test",
    )
    res_none = engine.fuse([ev_none], dummy_high_quality)
    assert not np.isnan(res_none["fused_authenticity_score"])
    assert not np.isnan(res_none["risk_score"])
    assert not np.isnan(res_none["uncertainty"])

    # Case C: Extreme scores stay clipped
    ev_extreme = EvidenceObject(
        type=EvidenceType.LOGO,
        score=1.0,
        confidence=1.0,
        quality=1.0,
        availability=True,
        source="test-extreme",
        explanation="Max score test",
    )
    res_extreme = engine.fuse([ev_extreme], dummy_high_quality)
    assert res_extreme["fused_authenticity_score"] <= 0.98
    assert res_extreme["fused_authenticity_score"] >= 0.05


def test_fusion_coverage_uncertainty_monotonicity(dummy_high_quality):
    """
    Tests that increasing evidence coverage monotonically reduces uncertainty.
    """
    engine = MultiEvidenceFusionEngine()

    def make_ev(t: EvidenceType, score: float = 0.90):
        return EvidenceObject(
            type=t,
            score=score,
            confidence=0.90,
            quality=0.90,
            availability=True,
            source=f"test-{t.value}",
            explanation="Normal evidence",
        )

    # 1 evidence engine
    f1 = engine.fuse([make_ev(EvidenceType.LOGO)], dummy_high_quality)
    # 4 evidence engines
    f4 = engine.fuse([
        make_ev(EvidenceType.LOGO),
        make_ev(EvidenceType.LAYOUT),
        make_ev(EvidenceType.COLOUR),
        make_ev(EvidenceType.SEAL),
    ], dummy_high_quality)
    # 8 evidence engines
    f8 = engine.fuse([
        make_ev(EvidenceType.LOGO),
        make_ev(EvidenceType.LAYOUT),
        make_ev(EvidenceType.COLOUR),
        make_ev(EvidenceType.SEAL),
        make_ev(EvidenceType.TYPOGRAPHY),
        make_ev(EvidenceType.TEXTURE),
        make_ev(EvidenceType.BARCODE),
        make_ev(EvidenceType.OCR),
    ], dummy_high_quality)

    assert f1["evidence_coverage"] < f4["evidence_coverage"] < f8["evidence_coverage"]
    # Higher coverage must strictly yield lower or equal uncertainty
    assert f1["uncertainty"] > f4["uncertainty"] > f8["uncertainty"]


# ---------------------------------------------------------------------------
# 2. Gatekeeper & Decision State Correctness
# ---------------------------------------------------------------------------
def test_seal_tamper_gatekeeper_overrides_high_branding(dummy_high_quality):
    """
    Tests that a compromised heat seal (<0.35) forces TAMPERED_OR_DAMAGED with risk >= 75.0
    and DO NOT CONSUME guidance, even when exterior logo is 100% authentic.
    """
    decision_engine = DecisionEngine()
    ev_logo = EvidenceObject(
        type=EvidenceType.LOGO,
        score=0.98,
        confidence=0.95,
        availability=True,
        source="logo-test",
        explanation="Genuine branding",
    )
    ev_seal = EvidenceObject(
        type=EvidenceType.SEAL,
        score=0.15,  # Severely compromised
        confidence=0.95,
        availability=True,
        source="seal-test",
        explanation="Crimp broken",
        regions=[{"x_min": 0.10, "y_min": 0.10, "x_max": 0.60, "y_max": 0.60}],
    )

    fusion = {
        "fused_authenticity_score": 0.40,
        "risk_score": 60.0,
        "confidence": 0.90,
        "uncertainty": 0.20,
        "evidence_coverage": 0.80,
        "conflicts": ["CONTRADICTION: Logo genuine but seal compromised"],
    }

    decision = decision_engine.evaluate(
        fusion_result=fusion,
        quality_result=dummy_high_quality,
        evidences=[ev_logo, ev_seal],
        product_identified=True,
    )

    assert decision.state == DecisionState.TAMPERED_OR_DAMAGED
    assert decision.risk_score >= 75.0
    assert "DO NOT CONSUME" in decision.recommendation
    assert "SEAL_INTEGRITY_COMPROMISED" in decision.reason_codes


def test_abstention_gatekeeper_coverage_and_uncertainty(dummy_high_quality):
    """
    Tests that if coverage < 0.50 or uncertainty > 0.65, the system abstains
    with INSUFFICIENT_EVIDENCE and risk score 50.0.
    """
    decision_engine = DecisionEngine()

    # Low coverage abstention
    fusion_low_cov = {
        "fused_authenticity_score": 0.95,
        "risk_score": 5.0,
        "confidence": 0.90,
        "uncertainty": 0.55,
        "evidence_coverage": 0.25,  # Below 0.50 threshold
        "conflicts": [],
    }
    dec_low_cov = decision_engine.evaluate(
        fusion_result=fusion_low_cov,
        quality_result=dummy_high_quality,
        evidences=[],
        product_identified=True,
    )
    assert dec_low_cov.state == DecisionState.INSUFFICIENT_EVIDENCE
    assert dec_low_cov.risk_score == 50.0
    assert any("INSUFFICIENT_EVIDENCE_ABSTENTION" in r for r in dec_low_cov.reason_codes)

    # High uncertainty abstention
    fusion_high_unc = {
        "fused_authenticity_score": 0.90,
        "risk_score": 10.0,
        "confidence": 0.40,
        "uncertainty": 0.72,  # Above 0.65 threshold
        "evidence_coverage": 0.60,
        "conflicts": [],
    }
    dec_high_unc = decision_engine.evaluate(
        fusion_result=fusion_high_unc,
        quality_result=dummy_high_quality,
        evidences=[],
        product_identified=True,
    )
    assert dec_high_unc.state == DecisionState.INSUFFICIENT_EVIDENCE
    assert dec_high_unc.risk_score == 50.0


def test_competitor_brand_rejection(dummy_high_quality):
    """
    Tests that non-Amul brands (e.g. Mother Dairy, Nandini) trigger UNSUPPORTED_PRODUCT.
    """
    decision_engine = DecisionEngine()
    fusion = {
        "fused_authenticity_score": 0.0,
        "risk_score": 0.0,
        "confidence": 0.90,
        "uncertainty": 0.10,
        "evidence_coverage": 0.0,
        "conflicts": [],
    }
    decision = decision_engine.evaluate(
        fusion_result=fusion,
        quality_result=dummy_high_quality,
        evidences=[],
        is_packaging=True,
        is_supported_brand=False,
        detected_brand="MOTHER DAIRY",
    )
    assert decision.state == DecisionState.UNSUPPORTED_PRODUCT
    assert "UNSUPPORTED_BRAND" in decision.reason_codes
    assert "DETECTED_BRAND_MOTHER_DAIRY" in decision.reason_codes


def test_duplicate_view_detection_in_decision_engine(dummy_high_quality):
    """
    Tests that duplicate views (two front panels) trigger INSUFFICIENT_EVIDENCE with DUPLICATE_VIEW_SUBMITTED.
    """
    decision_engine = DecisionEngine()
    fusion = {
        "fused_authenticity_score": 0.50,
        "risk_score": 50.0,
        "confidence": 0.30,
        "uncertainty": 0.85,
        "evidence_coverage": 0.0,
        "conflicts": [],
    }
    decision = decision_engine.evaluate(
        fusion_result=fusion,
        quality_result=dummy_high_quality,
        evidences=[],
        duplicate_views=True,
    )
    assert decision.state == DecisionState.INSUFFICIENT_EVIDENCE
    assert "DUPLICATE_VIEW_SUBMITTED" in decision.reason_codes
    assert "Both submitted images appear to be the same packaging panel" in decision.recommendation


# ---------------------------------------------------------------------------
# 3. Fault Isolation & Determinism
# ---------------------------------------------------------------------------
def test_safe_analyze_fault_isolation_barrier():
    """
    Tests that _safe_analyze captures exceptions thrown by evidence analyzers,
    returning availability=False rather than crashing.
    """
    def broken_analyzer(*args, **kwargs):
        raise ValueError("Simulated CV2 error during SIFT feature detection")

    ev = AIOrchestrator._safe_analyze(
        broken_analyzer,
        ev_type=EvidenceType.LOGO,
        source="test-broken-engine",
    )

    assert isinstance(ev, EvidenceObject)
    assert not ev.availability
    assert ev.score is None
    assert ev.confidence == 0.10
    assert "Simulated CV2 error" in ev.features.get("error", "")
    assert "unavailable due to engine exception" in ev.explanation


def test_decision_reproducibility_deterministic():
    """
    Tests that the MultiEvidenceFusionEngine and DecisionEngine are 100% deterministic
    across multiple executions on the same evidence objects.
    """
    fusion_engine = MultiEvidenceFusionEngine()
    decision_engine = DecisionEngine()
    quality = QualityAssessmentResult(
        resolution_score=0.90, blur_score=0.90, brightness_score=0.90,
        contrast_score=0.90, glare_score=0.90, occlusion_score=0.90,
        overall_quality=0.90, usable=True
    )

    evidences = [
        EvidenceObject(type=EvidenceType.LOGO, score=0.92, confidence=0.88, availability=True, source="s1", explanation="Logo normal"),
        EvidenceObject(type=EvidenceType.LAYOUT, score=0.87, confidence=0.85, availability=True, source="s2", explanation="Layout normal"),
        EvidenceObject(type=EvidenceType.COLOUR, score=0.91, confidence=0.90, availability=True, source="s3", explanation="Colour normal"),
        EvidenceObject(type=EvidenceType.SEAL, score=0.89, confidence=0.87, availability=True, source="s4", explanation="Seal normal"),
        EvidenceObject(type=EvidenceType.BARCODE, score=0.95, confidence=0.92, availability=True, source="s5", explanation="Barcode normal"),
        EvidenceObject(type=EvidenceType.OCR, score=0.88, confidence=0.86, availability=True, source="s6", explanation="OCR normal"),
    ]

    fused_scores = []
    risk_scores = []
    states = []

    for _ in range(10):
        f = fusion_engine.fuse(evidences, quality)
        d = decision_engine.evaluate(f, quality, evidences, product_identified=True)
        fused_scores.append(f["fused_authenticity_score"])
        risk_scores.append(f["risk_score"])
        states.append(d.state.value)

    assert len(set(fused_scores)) == 1, "Fused scores must be perfectly deterministic"
    assert len(set(risk_scores)) == 1, "Risk scores must be perfectly deterministic"
    assert len(set(states)) == 1, "Decision states must be perfectly deterministic"
