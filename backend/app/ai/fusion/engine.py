from typing import Any, Dict, List, Tuple
import numpy as np
from backend.app.ai.contracts import EvidenceObject, EvidenceType, QualityAssessmentResult


class ConflictDetector:
    """
    Identifies contradictory signals across independent visual, textual, and machine-readable engines.
    Applies pairwise contradiction detection to spot adversarial replicas or tampered packages.
    """
    @staticmethod
    def detect_conflicts(evidences: List[EvidenceObject]) -> Tuple[List[str], float]:
        ev_map = {e.type.value: e for e in evidences if e.availability and e.score is not None}
        conflicts: List[str] = []
        penalty: float = 0.0

        # Conflict 1: Strong visual resemblance but Barcode mismatch
        logo_ev = ev_map.get(EvidenceType.LOGO.value)
        barcode_ev = ev_map.get(EvidenceType.BARCODE.value)

        if logo_ev and barcode_ev:
            if logo_ev.score > 0.80 and barcode_ev.score < 0.30:
                conflicts.append(
                    "CONTRADICTION: Logo geometry matches reference, but barcode is inconsistent with registered packaging."
                )
                penalty += 0.20

        # Conflict 2: Authentic exterior but Tampered/Compromised Seal
        seal_ev = ev_map.get(EvidenceType.SEAL.value)
        if seal_ev and logo_ev:
            if seal_ev.score < 0.35 and logo_ev.score > 0.75:
                conflicts.append(
                    "CONTRADICTION: Brand artwork appears genuine, but heat-seal crimp band exhibits physical tampering anomalies."
                )
                penalty += 0.25

        # Conflict 3: QR destination suspicious despite valid OCR
        qr_ev = ev_map.get(EvidenceType.QR.value)
        ocr_ev = ev_map.get(EvidenceType.OCR.value)
        if qr_ev and ocr_ev:
            if qr_ev.score < 0.40 and ocr_ev.score > 0.80:
                conflicts.append(
                    "CONTRADICTION: Packaging text is consistent, but QR code routes to an unverified non-brand domain."
                )
                penalty += 0.15

        penalty = float(np.clip(penalty, 0.0, 0.45))
        return conflicts, penalty


class MultiEvidenceFusionEngine:
    """
    Quality- and Certainty-Modulated Weighted Evidence Fusion with Multiplicative Contradiction Penalty.

    MATHEMATICAL SPECIFICATION:
    1. Effective Weight Calculation:
       w_i = W_base(e_i.type) * c_i * q_i
       where W_base is the base engine weight, c_i is engine confidence, and q_i is local crop quality.

    2. Weighted Normalized Score:
       S_raw = (sum_{i=1}^M w_i * s_i) / (sum_{i=1}^M w_i)
       where s_i is the non-null conformity score of available evidence e_i.

    3. Contradiction Penalty Calculation:
       Delta_conflict = min(0.45, sum_k delta_k)
       where delta_k are pairwise contradiction penalties from ConflictDetector.

    4. Fused Authenticity Score:
       S_fused = clip(S_raw * (1.0 - Delta_conflict), 0.05, 0.98)

    5. Risk Score (Inverted 0-100 scale):
       Risk_Score = round((1.0 - S_fused) * 100.0, 1)

    6. Evidence Coverage:
       Coverage = Available_Count / Total_Expected_Types (12)

    7. Assessment Confidence:
       Confidence = 0.40 * Q_overall + 0.60 * mean(Q_evidence)

    8. Assessment Uncertainty:
       Uncertainty = clip(1.0 - (Coverage * Confidence * (1.0 - Delta_conflict)), 0.05, 0.95)
    """
    BASE_WEIGHTS = {
        EvidenceType.LOGO.value: 0.18,
        EvidenceType.LAYOUT.value: 0.12,
        EvidenceType.COLOUR.value: 0.10,
        EvidenceType.TYPOGRAPHY.value: 0.08,
        EvidenceType.TEXTURE.value: 0.06,
        EvidenceType.SHAPE.value: 0.08,
        EvidenceType.SEAL.value: 0.12,
        EvidenceType.PRINT.value: 0.06,
        EvidenceType.OCR.value: 0.10,
        EvidenceType.BARCODE.value: 0.05,
        EvidenceType.QR.value: 0.03,
        EvidenceType.CERTIFICATION.value: 0.02,
    }

    def fuse(
        self,
        evidences: List[EvidenceObject],
        quality_result: QualityAssessmentResult
    ) -> Dict[str, Any]:
        conflicts, conflict_penalty = ConflictDetector.detect_conflicts(evidences)

        total_weight = 0.0
        weighted_score_sum = 0.0
        available_count = 0
        qualities = []

        for ev in evidences:
            if not ev.availability or ev.score is None or np.isnan(ev.score):
                continue

            # Guard against invalid confidence or quality values
            conf = float(np.clip(ev.confidence if ev.confidence is not None and not np.isnan(ev.confidence) else 0.5, 0.01, 1.0))
            qual = float(np.clip(ev.quality if ev.quality is not None and not np.isnan(ev.quality) else 0.5, 0.01, 1.0))
            score = float(np.clip(ev.score, 0.0, 1.0))

            available_count += 1
            qualities.append(qual)
            base_w = self.BASE_WEIGHTS.get(ev.type.value, 0.05)

            # Effective weight calculation
            w_eff = base_w * conf * qual
            total_weight += w_eff
            weighted_score_sum += w_eff * score

        # Avoid zero division or NaN
        if total_weight <= 0.0 or np.isnan(total_weight) or np.isnan(weighted_score_sum):
            raw_fused_score = 0.50
        else:
            raw_fused_score = float(weighted_score_sum / total_weight)

        # Dampen by contradiction penalty
        fused_score = float(np.clip(raw_fused_score * (1.0 - conflict_penalty), 0.05, 0.98))

        # Risk score is inverted scale (0 = Lowest Risk, 100 = Highest Counterfeit/Tamper Risk)
        risk_score = float(round(np.clip((1.0 - fused_score) * 100.0, 0.0, 100.0), 1))

        # Evidence Coverage
        total_expected_types = len(self.BASE_WEIGHTS)
        evidence_coverage = float(round(available_count / total_expected_types, 2))

        # Confidence & Uncertainty Calibration
        mean_quality = float(np.mean(qualities)) if qualities else 0.5
        overall_q = quality_result.overall_quality if (quality_result and quality_result.overall_quality is not None and not np.isnan(quality_result.overall_quality)) else 0.5
        composite_confidence = float(round(np.clip(overall_q * 0.40 + mean_quality * 0.60, 0.05, 0.99), 3))
        uncertainty = float(round(np.clip(1.0 - (evidence_coverage * composite_confidence * (1.0 - conflict_penalty)), 0.05, 0.95), 3))

        return {
            "fused_authenticity_score": round(fused_score, 3),
            "risk_score": risk_score,
            "confidence": composite_confidence,
            "uncertainty": uncertainty,
            "evidence_coverage": evidence_coverage,
            "conflicts": conflicts,
            "conflict_penalty": round(conflict_penalty, 3)
        }
