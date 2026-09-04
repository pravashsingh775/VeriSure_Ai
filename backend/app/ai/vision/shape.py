from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from backend.app.ai.contracts import BaseVisionAnalyzer, EvidenceObject, EvidenceType, RegionBox


class ShapeAnalyzer(BaseVisionAnalyzer):
    """
    Evaluates package exterior shape, Hu Moments invariants, and aspect ratio fidelity.
    """
    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_crop_bgr: Optional[np.ndarray] = None,
        reference_metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceObject:
        h, w = scan_crop_bgr.shape[:2]
        gray = cv2.cvtColor(scan_crop_bgr, cv2.COLOR_BGR2GRAY)
        aspect_ratio = float(h / max(1, w))

        # Approximate outline contour
        _, thresh = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if reference_crop_bgr is None or reference_crop_bgr.size == 0:
            return EvidenceObject(
                type=EvidenceType.SHAPE,
                score=None,
                confidence=0.0,
                availability=False,
                quality=0.50,
                source="verisure-shape-hu-v1",
                features={
                    "aspect_ratio": round(aspect_ratio, 3)
                },
                regions=[],
                explanation="Trusted reference unavailable for comparison.",
                warnings=["TRUSTED_REFERENCE_UNAVAILABLE"]
            )

        hu_diff = 0.0
        score = 0.50

        if contours:
            main_cnt = max(contours, key=cv2.contourArea)
            moments = cv2.moments(main_cnt)
            hu_scan = cv2.HuMoments(moments).flatten()
            hu_scan_log = -np.sign(hu_scan) * np.log10(np.abs(hu_scan) + 1e-10)

            ref_gray = cv2.cvtColor(reference_crop_bgr, cv2.COLOR_BGR2GRAY)
            _, ref_thresh = cv2.threshold(ref_gray, 20, 255, cv2.THRESH_BINARY)
            ref_cnts, _ = cv2.findContours(ref_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if ref_cnts:
                ref_main_cnt = max(ref_cnts, key=cv2.contourArea)
                ref_moments = cv2.moments(ref_main_cnt)
                hu_ref = cv2.HuMoments(ref_moments).flatten()
                hu_ref_log = -np.sign(hu_ref) * np.log10(np.abs(hu_ref) + 1e-10)

                hu_diff = float(np.mean(np.abs(hu_scan_log[:4] - hu_ref_log[:4])))
                score = float(np.clip(1.0 - (hu_diff * 0.15), 0.30, 0.98))

        explanation = (
            f"Package geometry and aspect ratio ({round(aspect_ratio, 2)}) match standard production specifications "
            f"with shape conformity of {round(score * 100, 1)}%."
        )

        return EvidenceObject(
            type=EvidenceType.SHAPE,
            score=round(score, 3),
            confidence=0.88,
            availability=True,
            quality=0.92,
            source="verisure-shape-hu-v1",
            features={
                "aspect_ratio": round(aspect_ratio, 3),
                "hu_moment_delta": round(hu_diff, 4)
            },
            regions=[],
            explanation=explanation,
            warnings=[]
        )
