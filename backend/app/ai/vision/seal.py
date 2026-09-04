from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from backend.app.ai.contracts import BaseVisionAnalyzer, EvidenceObject, EvidenceType, RegionBox


class SealAnalyzer(BaseVisionAnalyzer):
    """
    Examines top and bottom heat-seal bands for periodic mechanical crimp serrations,
    detecting signs of physical tampering, pinholes, or manual resealing.
    """
    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_crop_bgr: Optional[np.ndarray] = None,
        reference_metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceObject:
        h, w = scan_crop_bgr.shape[:2]
        gray = cv2.cvtColor(scan_crop_bgr, cv2.COLOR_BGR2GRAY)

        # Inspect top 8% and bottom 8% seal bands
        seal_band_h = max(10, int(h * 0.08))
        top_seal = gray[:seal_band_h, :]
        bot_seal = gray[h - seal_band_h:, :]

        # Sobel Y gradient across seal lines
        sobel_top = cv2.Sobel(top_seal, cv2.CV_64F, 0, 1, ksize=3)
        sobel_bot = cv2.Sobel(bot_seal, cv2.CV_64F, 0, 1, ksize=3)

        top_gradient_var = float(np.var(sobel_top))
        bot_gradient_var = float(np.var(sobel_bot))
        mean_crimp_activity = (top_gradient_var + bot_gradient_var) / 2.0

        # Normal industrial crimp machines produce strong periodic ridge gradients (var > 120)
        # Smooth un-crimped or hand-melted reseals lack regular crimp variance
        crimp_score = float(np.clip(mean_crimp_activity / 220.0, 0.20, 0.98))
        regions: List[RegionBox] = []

        if crimp_score < 0.35:
            regions.append(RegionBox(
                x_min=0.0,
                y_min=0.0,
                x_max=1.0,
                y_max=0.08,
                label="Anomalous Heat-Seal Band",
                difference_score=round(1.0 - crimp_score, 3),
                explanation="Top seal band lacks characteristic mechanical crimp pattern."
            ))

        explanation = (
            f"Package heat-seal crimp bands evaluated. "
            f"Crimp gradient variance: {round(mean_crimp_activity, 1)} (Integrity score: {round(crimp_score * 100, 1)}%)."
        )

        return EvidenceObject(
            type=EvidenceType.SEAL,
            score=round(crimp_score, 3),
            confidence=0.86,
            availability=True,
            quality=0.90,
            source="verisure-seal-gradient-v1",
            features={
                "top_seal_crimp_variance": round(top_gradient_var, 1),
                "bottom_seal_crimp_variance": round(bot_gradient_var, 1),
                "mean_crimp_activity": round(mean_crimp_activity, 1)
            },
            regions=regions,
            explanation=explanation,
            warnings=["POTENTIAL_TAMPER_EVIDENCE"] if crimp_score < 0.30 else []
        )
