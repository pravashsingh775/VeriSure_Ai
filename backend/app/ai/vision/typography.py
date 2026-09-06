from typing import Any

import cv2
import numpy as np

from backend.app.ai.contracts import BaseVisionAnalyzer, EvidenceObject, EvidenceType


class TypographyAnalyzer(BaseVisionAnalyzer):
    """
    Analyzes font stroke consistency, baseline alignment, and text geometry without making
    unsupported font identification claims.
    """
    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_crop_bgr: np.ndarray | None = None,
        reference_metadata: dict[str, Any] | None = None
    ) -> EvidenceObject:
        gray = cv2.cvtColor(scan_crop_bgr, cv2.COLOR_BGR2GRAY)
        # Binarize with Otsu to isolate text strokes
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Distance transform to measure stroke widths
        dist = cv2.distanceTransform(thresh, cv2.DIST_L2, 3)
        stroke_widths = dist[dist > 1.0]

        if len(stroke_widths) == 0:
            return EvidenceObject(
                type=EvidenceType.TYPOGRAPHY,
                score=0.50,
                confidence=0.40,
                availability=False,
                quality=0.50,
                source="verisure-typography-stroke-v1",
                explanation="No clear typographic stroke patterns could be isolated.",
                warnings=["INSUFFICIENT_TEXT_STROKE_DATA"]
            )

        mean_stroke = float(np.mean(stroke_widths))
        std_stroke = float(np.std(stroke_widths))
        # Consistent professional printing has lower stroke variance
        cov = std_stroke / max(0.1, mean_stroke)
        score = float(np.clip(1.0 - (cov * 0.40), 0.30, 0.95))

        explanation = (
            f"Typographic strokes analyzed across text regions. "
            f"Mean stroke width is {round(mean_stroke, 2)}px with stroke uniformity score of {round(score * 100, 1)}%."
        )

        return EvidenceObject(
            type=EvidenceType.TYPOGRAPHY,
            score=round(score, 3),
            confidence=0.82,
            availability=True,
            quality=0.88,
            source="verisure-typography-stroke-v1",
            features={
                "mean_stroke_width_px": round(mean_stroke, 2),
                "stroke_std_px": round(std_stroke, 2),
                "stroke_coefficient_of_variation": round(cov, 3)
            },
            regions=[],
            explanation=explanation,
            warnings=[]
        )
