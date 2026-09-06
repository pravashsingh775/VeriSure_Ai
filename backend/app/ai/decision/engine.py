from typing import Any

from backend.app.ai.contracts import DecisionResult, DecisionState, EvidenceObject, EvidenceType, QualityAssessmentResult


class DecisionEngine:
    """
    Translates fused quantitative evidence and uncertainty bounds into standardized
    decision states, reason codes, and consumer advisory actions.
    """
    def evaluate(
        self,
        fusion_result: dict[str, Any],
        quality_result: QualityAssessmentResult,
        evidences: list[EvidenceObject],
        product_identified: bool = True,
        is_packaging: bool = True,
        packaging_category: str = "PHYSICAL_PACKAGING",
        detected_brand: str | None = None,
        is_supported_brand: bool = True,
        brand_reason: str | None = None,
        duplicate_views: bool = False
    ) -> DecisionResult:
        risk_score = fusion_result["risk_score"]
        confidence = fusion_result["confidence"]
        uncertainty = fusion_result["uncertainty"]
        coverage = fusion_result["evidence_coverage"]
        conflicts = fusion_result.get("conflicts", [])

        # Collect reason codes
        reason_codes: list[str] = []
        ev_map = {e.type.value: e for e in evidences if e.availability and e.score is not None}

        # 0. Domain & Non-Packaging Gate (Diagrams, schematics, documents, screenshots)
        if not is_packaging:
            return DecisionResult(
                state=DecisionState.INSUFFICIENT_EVIDENCE,
                risk_score=0.0,
                confidence=0.10,
                uncertainty=0.95,
                evidence_coverage=0.0,
                recommendation="Please upload a clear photograph of a physical Amul flexible milk pouch.",
                reason_codes=["NOT_PHYSICAL_PACKAGING", f"DETECTED_{packaging_category.upper()}"],
                explanation_summary=(
                    "The uploaded image is not a physical flexible milk pouch packaging "
                    f"(detected: {packaging_category.lower().replace('_', ' ')}). VeriSure AI requires "
                    "a photograph of physical FMCG dairy packaging to conduct authenticity risk analysis."
                ),
                contradictions=[],
                suspicious_regions=[]
            )

        # 1. Competitor / Unsupported Brand Gate (e.g. Mother Dairy, Nandini, Nestle)
        if not is_supported_brand and detected_brand and detected_brand != "UNKNOWN":
            return DecisionResult(
                state=DecisionState.UNSUPPORTED_PRODUCT,
                risk_score=0.0,
                confidence=0.90,
                uncertainty=0.10,
                evidence_coverage=coverage,
                recommendation=(
                    "System currently supports Amul dairy packaging only. "
                    "Please upload an Amul milk pouch (Amul Gold, Amul Taaza, or Amul Shakti)."
                ),
                reason_codes=["UNSUPPORTED_BRAND", f"DETECTED_BRAND_{detected_brand.upper().replace(' ', '_')}"],
                explanation_summary=(
                    f"Unsupported Brand Detected: This product appears to be '{detected_brand}'. "
                    "VeriSure AI V1 is calibrated specifically for Amul flexible milk pouches "
                    "(Amul Gold, Amul Taaza, Amul Shakti). Authenticity verification cannot be performed "
                    f"on unsupported or competitor brand packaging."
                ),
                contradictions=[],
                suspicious_regions=[]
            )

        # 1.5 Duplicate-View Gate (e.g. Case D: Two front panels or duplicate pair)
        if duplicate_views:
            return DecisionResult(
                state=DecisionState.INSUFFICIENT_EVIDENCE,
                risk_score=50.0,
                confidence=0.30,
                uncertainty=0.85,
                evidence_coverage=coverage,
                recommendation=(
                    "Both submitted images appear to be the same packaging panel or identical views. "
                    "Dual-side verification requires one Front panel and one Back panel image."
                ),
                reason_codes=["DUPLICATE_VIEW_SUBMITTED", "MISSING_COMPLEMENTARY_PANEL"],
                explanation_summary=(
                    "Dual-side verification aborted: Duplicate or identical packaging panel detected. "
                    "Please capture and submit both the Front and Back panels of the physical package."
                ),
                contradictions=conflicts,
                suspicious_regions=[]
            )

        # 2. Quality gate
        if not quality_result.usable:
            return DecisionResult(
                state=DecisionState.INSUFFICIENT_EVIDENCE,
                risk_score=50.0,
                confidence=0.30,
                uncertainty=0.90,
                evidence_coverage=coverage,
                recommendation=quality_result.guidance or "Please capture a sharper, clearer image.",
                reason_codes=["IMAGE_QUALITY_INSUFFICIENT"] + quality_result.reasons,
                explanation_summary="Evidence cannot be reliably verified due to adverse image capture conditions (glare, blur, or severe underexposure).",
                contradictions=[],
                suspicious_regions=[]
            )

        # 3. Product identity gate
        if not product_identified:
            return DecisionResult(
                state=DecisionState.UNSUPPORTED_PRODUCT,
                risk_score=0.0,
                confidence=0.30,
                uncertainty=0.85,
                evidence_coverage=coverage,
                recommendation="System can only verify Amul product packaging (Amul Gold, Amul Taaza, Amul Shakti). Please upload a valid Amul milk pouch.",
                reason_codes=["UNRECOGNIZED_PACKAGING_OR_BRAND"],
                explanation_summary="The detected packaging does not match any registered product variant or authorized Amul packaging version in the factory reference corpus.",
                contradictions=[],
                suspicious_regions=[]
            )

        # 4. Seal integrity gate
        seal_ev = ev_map.get(EvidenceType.SEAL.value)
        if seal_ev and seal_ev.score is not None and seal_ev.score < 0.35:
            reason_codes.append("SEAL_INTEGRITY_COMPROMISED")
            return DecisionResult(
                state=DecisionState.TAMPERED_OR_DAMAGED,
                risk_score=max(75.0, risk_score),
                confidence=confidence,
                uncertainty=uncertainty,
                evidence_coverage=coverage,
                recommendation="DO NOT CONSUME. Physical seal lines indicate potential puncture, tampering, or improper manual reseal.",
                reason_codes=reason_codes,
                explanation_summary="Heat-seal crimp analysis identified anomalous ridge patterns inconsistent with automated industrial packaging machinery.",
                contradictions=conflicts,
                suspicious_regions=seal_ev.regions
            )

        # 5. Explicit Abstention Gate (Coverage < 0.50 or Uncertainty > 0.65)
        if coverage < 0.50 or uncertainty > 0.65:
            abstain_reasons = []
            if coverage < 0.50:
                abstain_reasons.append(f"Evidence coverage of {round(coverage * 100, 1)}% is below minimum required 50% threshold")
            if uncertainty > 0.65:
                abstain_reasons.append(f"Assessment uncertainty of {round(uncertainty * 100, 1)}% exceeds maximum 65% bound")

            return DecisionResult(
                state=DecisionState.INSUFFICIENT_EVIDENCE,
                risk_score=50.0,
                confidence=confidence,
                uncertainty=uncertainty,
                evidence_coverage=coverage,
                recommendation="Evidence is insufficient to reach a reliable authenticity risk assessment. Please upload clearer images showing additional packaging panels.",
                reason_codes=["INSUFFICIENT_EVIDENCE_ABSTENTION"] + abstain_reasons,
                explanation_summary="System abstained from risk classification: " + "; ".join(abstain_reasons) + ".",
                contradictions=conflicts,
                suspicious_regions=[]
            )

        # 6. Standard Risk Classification Matrix
        if logo_ev := ev_map.get(EvidenceType.LOGO.value):
            if logo_ev.score > 0.85:
                reason_codes.append("LOGO_CONGRUENT")
            elif logo_ev.score < 0.50:
                reason_codes.append("LOGO_MISMATCH")

        if barcode_ev := ev_map.get(EvidenceType.BARCODE.value):
            if barcode_ev.score > 0.90:
                reason_codes.append("BARCODE_VERIFIED")
            elif barcode_ev.score < 0.40:
                reason_codes.append("BARCODE_MISMATCH")

        if conflicts:
            reason_codes.append("EVIDENCE_CONTRADICTIONS_PRESENT")

        if risk_score >= 70.0 or (conflicts and risk_score >= 50.0):
            state = DecisionState.CRITICAL_RISK
            rec = "HIGH COUNTERFEIT PROBABILITY. Do not consume. Report this package to brand customer care or local food safety authorities."
        elif risk_score >= 45.0:
            state = DecisionState.HIGH_RISK
            rec = "Significant deviations detected against registered packaging specifications. Exercise caution and verify purchase receipt."
        elif risk_score >= 20.0:
            state = DecisionState.MEDIUM_RISK
            rec = "Minor variations observed. Likely normal production batch variance or slight packaging redesign, but verify retail source. Note: Packaging evaluation cannot verify internal liquid contents."
        elif risk_score >= 10.0 or coverage < 0.65:
            state = DecisionState.LOW_RISK
            rec = "Low counterfeit risk based on available packaging evidence. This assessment cannot verify the chemical, biological, or internal contents of sealed packaging."
        else:
            state = DecisionState.LIKELY_GENUINE
            rec = "High packaging conformity against registered brand specifications. Note: Visual inspection cannot verify internal biological or chemical contents."

        explanation = (
            f"Overall risk score evaluated at {risk_score}/100 with confidence {round(confidence * 100, 1)}% "
            f"and evidence coverage of {round(coverage * 100, 1)}%. "
            f"{'Identified contradiction: ' + conflicts[0] if conflicts else 'No conflicting evidence detected.'}"
        )

        return DecisionResult(
            state=state,
            risk_score=risk_score,
            confidence=confidence,
            uncertainty=uncertainty,
            evidence_coverage=coverage,
            recommendation=rec,
            reason_codes=reason_codes,
            explanation_summary=explanation,
            contradictions=conflicts,
            suspicious_regions=[]
        )
