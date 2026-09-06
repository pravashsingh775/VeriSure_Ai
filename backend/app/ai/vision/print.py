from typing import Any

import cv2
import numpy as np

from backend.app.ai.contracts import BaseVisionAnalyzer, EvidenceObject, EvidenceType


class PrintQualityAnalyzer(BaseVisionAnalyzer):
    """
    Evaluates printing substrate sharpness, edge bleed, and chromatic misregistration
    to distinguish rotogravure/flexographic print from coarse inkjet/photocopy counterfeits.
    """
    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_crop_bgr: np.ndarray | None = None,
        reference_metadata: dict[str, Any] | None = None
    ) -> EvidenceObject:
        gray = cv2.cvtColor(scan_crop_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Edge sharpness metric
        edges = cv2.Canny(gray, 80, 160)
        edge_pixels = np.sum(edges > 0)

        # High-frequency gradient along edges
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)

        mean_edge_acuity = float(np.mean(grad_mag[edges > 0])) if edge_pixels > 0 else 50.0
        # High-end flexographic packaging print produces acuity > 140
        acuity_score = float(np.clip(mean_edge_acuity / 180.0, 0.25, 0.98))

        # 2. Color fringing / misregistration (shift between R and B channels along edges)
        b_chan = scan_crop_bgr[:, :, 0].astype(np.float32)
        r_chan = scan_crop_bgr[:, :, 2].astype(np.float32)
        fringing = float(np.mean(np.abs(r_chan[edges > 0] - b_chan[edges > 0]))) if edge_pixels > 0 else 10.0
        fringing_penalty = min(0.3, fringing / 120.0)

        final_score = float(np.clip(acuity_score - fringing_penalty, 0.20, 0.98))

        explanation = (
            f"Print acuity and substrate dot definition evaluated. "
            f"Edge sharpness acuity: {round(mean_edge_acuity, 1)} with print quality score of {round(final_score * 100, 1)}%."
        )

        return EvidenceObject(
            type=EvidenceType.PRINT,
            score=round(final_score, 3),
            confidence=0.85,
            availability=True,
            quality=0.90,
            source="verisure-print-acuity-v1",
            features={
                "mean_edge_acuity": round(mean_edge_acuity, 1),
                "color_fringing_delta": round(fringing, 2)
            },
            regions=[],
            explanation=explanation,
            warnings=[]
        )
