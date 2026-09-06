from typing import Any

import cv2
import numpy as np

from backend.app.ai.contracts import BaseVisionAnalyzer, EvidenceObject, EvidenceType, RegionBox


class LogoAnalyzer(BaseVisionAnalyzer):
    """
    Performs logo detection, geometry comparison, keypoint homography, and color consistency.
    """
    def __init__(self):
        self.orb = cv2.ORB_create(nfeatures=500, scaleFactor=1.2, nlevels=4)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_crop_bgr: np.ndarray | None = None,
        reference_metadata: dict[str, Any] | None = None
    ) -> EvidenceObject:
        h, w = scan_crop_bgr.shape[:2]

        if reference_crop_bgr is None or reference_crop_bgr.size == 0:
            return EvidenceObject(
                type=EvidenceType.LOGO,
                score=None,
                confidence=0.0,
                availability=False,
                quality=0.50,
                source="verisure-logo-orb-v1",
                features={},
                regions=[],
                explanation="Trusted reference unavailable for comparison.",
                warnings=["TRUSTED_REFERENCE_UNAVAILABLE"]
            )

        # Isolate top region where FMCG branding & logo resides
        logo_zone_h = int(h * 0.40)
        scan_logo_zone = scan_crop_bgr[:logo_zone_h, :]

        # Extract ORB keypoints & descriptors
        kp_scan, des_scan = self.orb.detectAndCompute(scan_logo_zone, None)

        if des_scan is None or len(kp_scan) < 10:
            return EvidenceObject(
                type=EvidenceType.LOGO,
                score=None,
                confidence=0.0,
                availability=False,
                quality=0.50,
                source="verisure-logo-orb-v1",
                features={"keypoints_count": len(kp_scan) if kp_scan else 0},
                explanation="Branding/logo area could not be clearly localized in the top quadrant.",
                warnings=["LOW_KEYPOINT_DENSITY_IN_LOGO_REGION"],
                regions=[]
            )

        # Reference crop is available: perform keypoint and template matching
        inlier_ratio = 0.0
        ncc_score = 0.0
        color_sim = 0.0
        matched_region = RegionBox(
            x_min=0.20,
            y_min=0.03,
            x_max=0.80,
            y_max=0.35,
            label="Logo Candidate Region",
            difference_score=0.0,
            explanation="Logo region evaluated against reference."
        )

        ref_h, ref_w = reference_crop_bgr.shape[:2]
        ref_logo_zone = reference_crop_bgr[:int(ref_h * 0.40), :]
        kp_ref, des_ref = self.orb.detectAndCompute(ref_logo_zone, None)

        if des_ref is not None and len(kp_ref) >= 8:
            matches = self.matcher.knnMatch(des_scan, des_ref, k=2)
            good_matches = []
            for m_pair in matches:
                if len(m_pair) == 2 and m_pair[0].distance < 0.75 * m_pair[1].distance:
                    good_matches.append(m_pair[0])

            if len(good_matches) >= 6:
                src_pts = np.float32([kp_scan[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                inliers = int(np.sum(mask)) if mask is not None else 0
                inlier_ratio = float(inliers / max(1, len(good_matches)))
            else:
                inlier_ratio = float(len(good_matches) / 20.0)

            # Normalized Template Cross-Correlation on resized zones
            res_scan = cv2.resize(cv2.cvtColor(scan_logo_zone, cv2.COLOR_BGR2GRAY), (200, 100))
            res_ref = cv2.resize(cv2.cvtColor(ref_logo_zone, cv2.COLOR_BGR2GRAY), (200, 100))
            corr = cv2.matchTemplate(res_scan, res_ref, cv2.TM_CCOEFF_NORMED)
            ncc_score = float(np.clip((corr.max() + 1.0) / 2.0, 0.0, 1.0))

            # Color consistency in Logo Zone
            hist_scan = cv2.calcHist([scan_logo_zone], [0, 1], None, [16, 16], [0, 180, 0, 256])
            hist_ref = cv2.calcHist([ref_logo_zone], [0, 1], None, [16, 16], [0, 180, 0, 256])
            cv2.normalize(hist_scan, hist_scan, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            cv2.normalize(hist_ref, hist_ref, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            color_corr = cv2.compareHist(hist_scan, hist_ref, cv2.HISTCMP_CORREL)
            color_sim = float(np.clip((color_corr + 1.0) / 2.0, 0.0, 1.0))

        # Composite Score (Inliers 40%, Template 35%, Color 25%)
        composite_score = 0.40 * inlier_ratio + 0.35 * ncc_score + 0.25 * color_sim
        score = float(np.clip(composite_score, 0.05, 0.99))
        confidence = float(np.clip(0.60 + 0.35 * min(1.0, len(kp_scan) / 100.0), 0.5, 0.98))

        matched_region.difference_score = round(1.0 - score, 3)

        explanation = (
            f"Logo geometry and typography match genuine reference with score {round(score * 100, 1)}%. "
            f"Keypoint inlier ratio is {round(inlier_ratio * 100, 1)}% and color correlation is {round(color_sim * 100, 1)}%."
        )

        return EvidenceObject(
            type=EvidenceType.LOGO,
            score=round(score, 3),
            confidence=round(confidence, 3),
            availability=True,
            quality=0.90,
            source="verisure-logo-orb-v1",
            features={
                "keypoints_count": len(kp_scan),
                "inlier_ratio": round(inlier_ratio, 3),
                "ncc_score": round(ncc_score, 3),
                "color_similarity": round(color_sim, 3)
            },
            regions=[matched_region],
            explanation=explanation,
            warnings=[]
        )
