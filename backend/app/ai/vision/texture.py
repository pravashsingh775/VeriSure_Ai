from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from skimage.feature import local_binary_pattern
from backend.app.ai.contracts import BaseVisionAnalyzer, EvidenceObject, EvidenceType, RegionBox


class TextureAnalyzer(BaseVisionAnalyzer):
    """
    Analyzes micro-texture and substrate finish using Local Binary Patterns (LBP) histograms.
    """
    def _compute_lbp_hist(self, gray: np.ndarray) -> np.ndarray:
        # Uniform LBP with P=8, R=1
        lbp = local_binary_pattern(gray, P=8, R=1, method="uniform")
        n_bins = int(lbp.max() + 1)
        hist, _ = np.histogram(lbp.ravel(), bins=n_bins, range=(0, n_bins), density=True)
        return hist.astype(np.float32)

    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_crop_bgr: Optional[np.ndarray] = None,
        reference_metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceObject:
        gray_scan = cv2.cvtColor(scan_crop_bgr, cv2.COLOR_BGR2GRAY)
        scan_hist = self._compute_lbp_hist(gray_scan)

        if reference_crop_bgr is None or reference_crop_bgr.size == 0:
            return EvidenceObject(
                type=EvidenceType.TEXTURE,
                score=None,
                confidence=0.0,
                availability=False,
                quality=0.50,
                source="verisure-texture-lbp-v1",
                features={
                    "pattern_entropy": round(float(-np.sum(scan_hist * np.log(scan_hist + 1e-7))), 3)
                },
                regions=[],
                explanation="Trusted reference unavailable for comparison.",
                warnings=["TRUSTED_REFERENCE_UNAVAILABLE"]
            )

        gray_ref = cv2.cvtColor(reference_crop_bgr, cv2.COLOR_BGR2GRAY)
        ref_hist = self._compute_lbp_hist(gray_ref)

        # Chi-square distance between LBP histograms
        eps = 1e-7
        chi2_dist = float(0.5 * np.sum(((scan_hist - ref_hist) ** 2) / (scan_hist + ref_hist + eps)))
        score = float(np.clip(1.0 - (chi2_dist * 2.5), 0.20, 0.98))

        explanation = (
            f"Substrate surface micro-texture evaluated via Local Binary Patterns (LBP). "
            f"Histogram similarity score: {round(score * 100, 1)}%."
        )

        return EvidenceObject(
            type=EvidenceType.TEXTURE,
            score=round(score, 3),
            confidence=0.85,
            availability=True,
            quality=0.90,
            source="verisure-texture-lbp-v1",
            features={
                "lbp_chi2_distance": round(chi2_dist, 4),
                "pattern_entropy": round(float(-np.sum(scan_hist * np.log(scan_hist + 1e-7))), 3)
            },
            regions=[],
            explanation=explanation,
            warnings=[]
        )
