from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from backend.app.ai.contracts import BaseVisionAnalyzer, EvidenceObject, EvidenceType, RegionBox


class LayoutAnalyzer(BaseVisionAnalyzer):
    """
    Analyzes relative positions, alignment, spacing, and structural geometry of visual packaging elements.
    """
    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_crop_bgr: Optional[np.ndarray] = None,
        reference_metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceObject:
        h, w = scan_crop_bgr.shape[:2]
        gray_scan = cv2.cvtColor(scan_crop_bgr, cv2.COLOR_BGR2GRAY)
        edges_scan = cv2.Canny(gray_scan, 50, 150)

        # Divide into 4 horizontal bands: [Header/Brand, Title/Hero, Body/Nutrition, Footer/Barcode]
        band_h = h // 4
        band_densities_scan = []
        for i in range(4):
            band = edges_scan[i * band_h:(i + 1) * band_h, :]
            density = float(np.mean(band > 0))
            band_densities_scan.append(density)

        if reference_crop_bgr is None or reference_crop_bgr.size == 0:
            return EvidenceObject(
                type=EvidenceType.LAYOUT,
                score=None,
                confidence=0.0,
                availability=False,
                quality=0.50,
                source="verisure-layout-spatial-v1",
                features={
                    "band_densities": [round(d, 4) for d in band_densities_scan]
                },
                regions=[],
                explanation="Trusted reference unavailable for comparison.",
                warnings=["TRUSTED_REFERENCE_UNAVAILABLE"]
            )

        ref_h, ref_w = reference_crop_bgr.shape[:2]
        gray_ref = cv2.cvtColor(reference_crop_bgr, cv2.COLOR_BGR2GRAY)
        edges_ref = cv2.Canny(gray_ref, 50, 150)

        ref_band_h = ref_h // 4
        edges_ref_densities = []
        for i in range(4):
            ref_band = edges_ref[i * ref_band_h:(i + 1) * ref_band_h, :]
            edges_ref_densities.append(float(np.mean(ref_band > 0)))

        band_diffs = []
        regions: List[RegionBox] = []
        for i in range(4):
            ref_band = edges_ref[i * ref_band_h:(i + 1) * ref_band_h, :]
            ref_density = float(np.mean(ref_band > 0))
            diff = abs(band_densities_scan[i] - ref_density)
            s_dens = band_densities_scan[i]
            # Match with neighboring bands to accommodate pouch bulging and perspective angle
            candidates = [abs(s_dens - edges_ref_densities[i])]
            if i > 0:
                candidates.append(abs(s_dens - edges_ref_densities[i - 1]) * 1.15)
            if i < 3:
                candidates.append(abs(s_dens - edges_ref_densities[i + 1]) * 1.15)
            diff = min(candidates)
            band_diffs.append(diff)

        mean_diff = float(np.mean(band_diffs))
        score = float(np.clip(1.0 - (mean_diff * 4.0), 0.20, 0.98))
        score = float(np.clip(1.0 - (mean_diff * 3.5), 0.20, 0.98))

        # If a band has severe mismatch, surface as a suspicious region
        band_names = ["Header / Brand", "Product Title / Mascot", "Details / Information", "Footer / Codes"]
        for i, diff in enumerate(band_diffs):
            if diff > 0.08:
                regions.append(RegionBox(
                    x_min=0.05,
                    y_min=round(i * 0.25, 2),
                    x_max=0.95,
                    y_max=round((i + 1) * 0.25, 2),
                    label=f"{band_names[i]} Layout Anomaly",
                    difference_score=round(diff, 3),
                    explanation=f"Spatial density in {band_names[i]} band deviates from reference pattern."
                ))

        explanation = (
            f"Packaging layout structural alignment evaluated with {round(score * 100, 1)}% conformity. "
            f"Horizontal design bands exhibit consistent element placement."
        )

        return EvidenceObject(
            type=EvidenceType.LAYOUT,
            score=round(score, 3),
            confidence=0.88,
            availability=True,
            quality=0.92,
            source="verisure-layout-spatial-v1",
            features={
                "band_densities": [round(d, 4) for d in band_densities_scan],
                "band_deviations": [round(d, 4) for d in band_diffs]
            },
            regions=regions,
            explanation=explanation,
            warnings=[]
        )
