from typing import Any, Dict, List, Optional
import cv2
import numpy as np
import zxingcpp
from backend.app.ai.contracts import EvidenceObject, EvidenceType, RegionBox


class BarcodeAnalyzer:
    """
    Decodes 1D barcodes (EAN-13, UPC) and validates check digits and catalog consistency.
    Explicitly clarifies: Barcode match is identity evidence, not proof of contents authenticity.
    """
    @staticmethod
    def _verify_ean13_checksum(code: str) -> bool:
        if not code.isdigit() or len(code) != 13:
            return False
        digits = [int(d) for d in code]
        # Sum odd positions (1x) and even positions (3x) for first 12 digits
        odd_sum = sum(digits[i] for i in range(0, 12, 2))
        even_sum = sum(digits[i] for i in range(1, 12, 2))
        total = odd_sum + (even_sum * 3)
        check_digit = (10 - (total % 10)) % 10
        return check_digit == digits[12]

    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceObject:
        decoded_values = []
        regions: List[RegionBox] = []
        h, w = scan_crop_bgr.shape[:2]

        # 1. Try zxingcpp decoder
        try:
            results = zxingcpp.read_barcodes(scan_crop_bgr)
            for res in results:
                if res.text:
                    decoded_values.append((res.text, str(res.format)))
        except Exception:
            pass

        # 2. Try OpenCV BarcodeDetector fallback if empty
        if not decoded_values and hasattr(cv2, "barcode") and hasattr(cv2.barcode, "BarcodeDetector"):
            try:
                detector = cv2.barcode.BarcodeDetector()
                ok, decoded_info, decoded_type, corners = detector.detectAndDecode(scan_crop_bgr)
                if ok and decoded_info:
                    for text, btype in zip(decoded_info, decoded_type):
                        if text:
                            decoded_values.append((text, btype))
            except Exception:
                pass

        expected_barcode = reference_metadata.get("expected_barcode") if reference_metadata else None

        if not decoded_values:
            # Barcode not visible or detectable in this view
            return EvidenceObject(
                type=EvidenceType.BARCODE,
                score=None,
                confidence=0.0,
                availability=False,
                status="UNAVAILABLE",
                quality=0.70,
                source="verisure-barcode-zxing-v1",
                explanation="No machine-readable 1D barcode was detectable in this image angle.",
                warnings=["BARCODE_NOT_DETECTED_IN_VIEW"]
            )

        code_val, code_format = decoded_values[0]
        checksum_valid = self._verify_ean13_checksum(code_val)

        score = 0.80
        warnings = []
        if checksum_valid:
            score += 0.10
        else:
            warnings.append("Barcode check digit does not satisfy modulo-10 checksum.")

        if expected_barcode:
            if code_val == expected_barcode:
                score = 0.98
                match_status = "matches registered packaging version"
            else:
                score = 0.20
                warnings.append(f"Decoded barcode ({code_val}) contradicts expected ({expected_barcode}).")
                match_status = "CONTRADICTS registered packaging version"
        else:
            match_status = "decoded successfully (no reference constraint supplied)"

        explanation = (
            f"1D Barcode ({code_format}) '{code_val}' decoded: {match_status}. "
            f"Note: Matching barcode verifies packaging metadata conformity, not physical content purity."
        )

        return EvidenceObject(
            type=EvidenceType.BARCODE,
            score=round(score, 3),
            confidence=0.98,
            availability=True,
            quality=0.95,
            source="verisure-barcode-zxing-v1",
            features={
                "decoded_value": code_val,
                "format": code_format,
                "checksum_valid": checksum_valid,
                "expected_barcode": expected_barcode
            },
            regions=regions,
            explanation=explanation,
            warnings=warnings
        )

