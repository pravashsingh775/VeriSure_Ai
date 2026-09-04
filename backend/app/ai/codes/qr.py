from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import cv2
import numpy as np
import zxingcpp
from backend.app.ai.contracts import EvidenceObject, EvidenceType, RegionBox


class QRAnalyzer:
    """
    Decodes QR codes, parses destination URLs, and evaluates brand domain safety.
    """
    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceObject:
        decoded_text = None
        h, w = scan_crop_bgr.shape[:2]

        # 1. Try zxingcpp for robust QR reading
        try:
            results = zxingcpp.read_barcodes(scan_crop_bgr)
            for res in results:
                if "QR" in str(res.format).upper():
                    decoded_text = res.text
                    break
        except Exception:
            pass

        # 2. Try OpenCV QRCodeDetector fallback
        if not decoded_text:
            try:
                qr_detector = cv2.QRCodeDetector()
                text, points, _ = qr_detector.detectAndDecode(scan_crop_bgr)
                if text:
                    decoded_text = text
            except Exception:
                pass

        if not decoded_text:
            return EvidenceObject(
                type=EvidenceType.QR,
                score=None,
                confidence=0.0,
                availability=False,
                status="UNAVAILABLE",
                quality=0.70,
                source="verisure-qr-decoder-v1",
                explanation="No 2D Quick Response (QR) code was isolated in this view.",
                warnings=["QR_CODE_NOT_DETECTED_IN_VIEW"]
            )

        # Domain safety analysis
        score = 0.85
        warnings = []
        is_url = False
        parsed_domain = None

        if decoded_text.startswith("http://") or decoded_text.startswith("https://"):
            is_url = True
            parsed = urlparse(decoded_text)
            parsed_domain = parsed.netloc.lower()

            trusted_domains = ["amul.com", "gcmmf.com", "amuldairy.com"]
            if any(t in parsed_domain for t in trusted_domains):
                score = 0.98
                domain_status = "Directs to verified brand domain."
            else:
                score = 0.35
                warnings.append(f"Destination domain '{parsed_domain}' is not in brand's trusted registry.")
                domain_status = "Destination domain is UNVERIFIED."
        else:
            domain_status = "Non-URL structured data string."

        explanation = (
            f"QR code decoded successfully: '{decoded_text[:80]}...'. {domain_status} "
            f"Note: QR routing verifies digital destination, not container tamper-resistance."
        )

        return EvidenceObject(
            type=EvidenceType.QR,
            score=round(score, 3),
            confidence=0.96,
            availability=True,
            quality=0.92,
            source="verisure-qr-decoder-v1",
            features={
                "decoded_text": decoded_text,
                "is_url": is_url,
                "parsed_domain": parsed_domain
            },
            regions=[],
            explanation=explanation,
            warnings=warnings
        )

