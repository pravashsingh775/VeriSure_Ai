from typing import Any

import cv2
import numpy as np

from backend.app.ai.contracts import BaseVisionAnalyzer, EvidenceObject, EvidenceType, RegionBox


class ColourAnalyzer(BaseVisionAnalyzer):
    """
    Evaluates color fidelity in CIELAB perceptual space, computing chromaticity Delta E
    while accounting for real-world lighting and shadow shifts.
    """
    def _extract_palette(self, img_bgr: np.ndarray, k: int = 4) -> np.ndarray:
        # Downsample for fast clustering
        small = cv2.resize(img_bgr, (100, 100))
        lab = cv2.cvtColor(small, cv2.COLOR_BGR2Lab)
        pixels = lab.reshape(-1, 3).astype(np.float32)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
        # Sort centers by frequency
        counts = np.bincount(labels.flatten())
        sorted_indices = np.argsort(-counts)
        return centers[sorted_indices]

    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_crop_bgr: np.ndarray | None = None,
        reference_metadata: dict[str, Any] | None = None
    ) -> EvidenceObject:
        scan_palette = self._extract_palette(scan_crop_bgr, k=4)

        if reference_crop_bgr is None or reference_crop_bgr.size == 0:
            return EvidenceObject(
                type=EvidenceType.COLOUR,
                score=None,
                confidence=0.0,
                availability=False,
                quality=0.50,
                source="verisure-colour-cielab-v1",
                features={
                    "dominant_lab_centers": [[round(float(c), 1) for c in color] for color in scan_palette]
                },
                regions=[],
                explanation="Trusted reference unavailable for comparison.",
                warnings=["TRUSTED_REFERENCE_UNAVAILABLE"]
            )

        ref_palette = self._extract_palette(reference_crop_bgr, k=4)
        regions: list[RegionBox] = []

        # Compute nearest-neighbor chromaticity Delta E between palettes (order-invariant)
        scan_to_ref_min = []
        for s_color in scan_palette:
            dists = []
            for r_color in ref_palette:
                dL = (s_color[0] - r_color[0]) * 0.35
                da = s_color[1] - r_color[1]
                db = s_color[2] - r_color[2]
                dists.append(np.sqrt(dL**2 + da**2 + db**2))
            scan_to_ref_min.append(min(dists))

        ref_to_scan_min = []
        for r_color in ref_palette:
            dists = []
            for s_color in scan_palette:
                dL = (s_color[0] - r_color[0]) * 0.35
                da = s_color[1] - r_color[1]
                db = s_color[2] - r_color[2]
                dists.append(np.sqrt(dL**2 + da**2 + db**2))
            ref_to_scan_min.append(min(dists))

        mean_delta_e = float((np.mean(scan_to_ref_min) + np.mean(ref_to_scan_min)) / 2.0)
        # Delta E < 6.0 is standard industrial print tolerance; > 20 is significant mismatch
        score = float(np.clip(1.0 - (mean_delta_e / 25.0), 0.20, 0.98))

        if mean_delta_e > 12.0:
            regions.append(RegionBox(
                x_min=0.1,
                y_min=0.1,
                x_max=0.9,
                y_max=0.9,
                label="Color Palette Deviation",
                difference_score=round(mean_delta_e / 25.0, 3),
                explanation=f"Overall chromaticity Delta E ({round(mean_delta_e, 1)}) exceeds normal industrial tolerance."
            ))

        explanation = (
            f"Packaging color spectrum evaluated in CIELAB perceptual space. "
            f"Mean chromaticity Delta E is {round(mean_delta_e, 1)} (Score: {round(score * 100, 1)}%)."
        )

        return EvidenceObject(
            type=EvidenceType.COLOUR,
            score=round(score, 3),
            confidence=0.90,
            availability=True,
            quality=0.94,
            source="verisure-colour-cielab-v1",
            features={
                "mean_delta_e": round(mean_delta_e, 2),
                "dominant_lab_centers": [[round(float(c), 1) for c in color] for color in scan_palette]
            },
            regions=regions,
            explanation=explanation,
            warnings=[]
        )
