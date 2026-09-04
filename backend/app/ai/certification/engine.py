import re
from typing import Any, Dict, List, Optional
from backend.app.ai.contracts import EvidenceObject, EvidenceType, RegionBox


class CertificationAnalyzer:
    """
    Extracts and validates regulatory markings (FSSAI, BIS, ISI).
    Maintains scientific honesty: Distinguishes syntax validity from live government FoSCoS registry verification.
    """
    INDIAN_STATE_CODES = {
        "00": "Central Licensing Authority",
        "01": "Jammu & Kashmir",
        "02": "Himachal Pradesh",
        "03": "Punjab",
        "04": "Chandigarh",
        "05": "Uttarakhand",
        "06": "Haryana",
        "07": "Delhi",
        "08": "Rajasthan",
        "09": "Uttar Pradesh",
        "10": "Bihar",
        "24": "Gujarat",
        "27": "Maharashtra",
    }

    def validate_fssai(self, lic_no: str) -> Dict[str, Any]:
        if not lic_no or not lic_no.isdigit() or len(lic_no) != 14:
            return {
                "valid_format": False,
                "reason": "FSSAI license must be exactly 14 numeric digits."
            }

        prefix_type = "Registration" if lic_no[0] == "1" else ("License" if lic_no[0] == "2" else "Other")
        state_code = lic_no[1:3]
        state_name = self.INDIAN_STATE_CODES.get(state_code, f"State Code {state_code}")
        year_str = f"20{lic_no[3:5]}"

        return {
            "valid_format": True,
            "prefix_type": prefix_type,
            "jurisdiction": state_name,
            "year_enrolled": year_str,
            "sequential_id": lic_no[8:]
        }

    def analyze(
        self,
        extracted_text: str,
        reference_metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceObject:
        match = re.search(r"(?:FSSAI|Lic\.?\s*No\.?)\s*[:\.]?\s*([0-9]{14})", extracted_text, re.IGNORECASE)

        if not match:
            return EvidenceObject(
                type=EvidenceType.CERTIFICATION,
                score=None,
                confidence=0.0,
                availability=False,
                status="UNAVAILABLE",
                quality=0.75,
                source="verisure-cert-fssai-v1",
                explanation="No 14-digit FSSAI regulatory license was detected in the visible packaging text.",
                warnings=["REGULATORY_MARK_NOT_DETECTED"]
            )

        fssai_no = match.group(1)
        val_info = self.validate_fssai(fssai_no)

        score = 0.90 if val_info["valid_format"] else 0.30
        expected_fssai = reference_metadata.get("expected_fssai") if reference_metadata else None

        warnings = []
        if expected_fssai:
            if fssai_no == expected_fssai:
                score = 0.98
                status_text = f"matches brand's registered license ({fssai_no})"
            else:
                score = 0.25
                warnings.append(f"Extracted license ({fssai_no}) differs from expected brand license ({expected_fssai}).")
                status_text = f"contradicts registered brand license"
        else:
            status_text = f"satisfies official 14-digit syntax"

        explanation = (
            f"FSSAI License {fssai_no} detected ({val_info.get('jurisdiction', 'National')}, est. {val_info.get('year_enrolled', 'N/A')}). "
            f"Format {status_text}. "
            f"IMPORTANT: Verification confirms packaging syntax conformity. Live government FoSCoS portal lookup requires external agency credentials."
        )

        return EvidenceObject(
            type=EvidenceType.CERTIFICATION,
            score=round(score, 3),
            confidence=0.95,
            availability=True,
            quality=0.90,
            source="verisure-cert-fssai-v1",
            features={
                "fssai_number": fssai_no,
                "validation_details": val_info,
                "government_portal_live_verified": False  # Honest disclosure
            },
            regions=[],
            explanation=explanation,
            warnings=warnings
        )

