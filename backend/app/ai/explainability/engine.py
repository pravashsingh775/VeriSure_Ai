import cv2
import numpy as np

from backend.app.ai.contracts import DecisionResult, EvidenceObject, RegionBox


class DifferenceHeatmapEngine:
    """
    Computes pixel-wise structural difference between normalized scan crop and reference template,
    overlaying an intuitive pseudo-color heatmap highlighting anomalous areas.
    """
    @staticmethod
    def generate_heatmap(
        scan_crop_bgr: np.ndarray,
        reference_crop_bgr: np.ndarray | None = None
    ) -> tuple[np.ndarray, list[RegionBox]]:
        h, w = scan_crop_bgr.shape[:2]
        regions: list[RegionBox] = []

        if reference_crop_bgr is None or reference_crop_bgr.size == 0:
            # Generate a neutral ambient overlay if reference image is missing
            overlay = scan_crop_bgr.copy()
            return overlay, regions

        # Resize reference to match scan dimensions
        ref_resized = cv2.resize(reference_crop_bgr, (w, h))
        # 1. Attempt feature-based homography alignment to correct camera perspective tilt
        ref_aligned = None
        try:
            orb = cv2.ORB_create(nfeatures=600)
            kp_scan, des_scan = orb.detectAndCompute(scan_crop_bgr, None)
            kp_ref, des_ref = orb.detectAndCompute(reference_crop_bgr, None)

            if des_scan is not None and des_ref is not None:
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                matches = bf.match(des_ref, des_scan)
                matches = sorted(matches, key=lambda m: m.distance)
                if len(matches) >= 8:
                    src_pts = np.float32([kp_ref[m.queryIdx].pt for m in matches[:60]]).reshape(-1, 1, 2)
                    dst_pts = np.float32([kp_scan[m.trainIdx].pt for m in matches[:60]]).reshape(-1, 1, 2)
                    H, inliers = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                    if H is not None and inliers is not None and np.sum(inliers) >= 6:
                        ref_aligned = cv2.warpPerspective(reference_crop_bgr, H, (w, h))
        except Exception:
            ref_aligned = None

        if ref_aligned is None or ref_aligned.size == 0:
            ref_aligned = ref_resized

        # 2. Structural Similarity (SSIM) Difference Map: D(x,y) = 1 - SSIM(x,y)
        scan_gray = cv2.cvtColor(scan_crop_bgr, cv2.COLOR_BGR2GRAY)
        ref_gray = cv2.cvtColor(ref_aligned, cv2.COLOR_BGR2GRAY)

        try:
            from skimage.metrics import structural_similarity as ssim
            _, ssim_map = ssim(scan_gray, ref_gray, full=True)
            diff_map = 1.0 - np.clip(ssim_map, 0.0, 1.0)
            diff_blurred = cv2.GaussianBlur(diff_map.astype(np.float32), (11, 11), 0)
            norm_diff = (np.clip(diff_blurred, 0.0, 1.0) * 255.0).astype(np.uint8)
        except Exception:
            diff = cv2.absdiff(scan_gray, ref_gray)
            diff_blurred = cv2.GaussianBlur(diff, (15, 15), 0)
            norm_diff = cv2.normalize(diff_blurred, None, 0, 255, cv2.NORM_MINMAX)

        # Apply JET colormap (Blue = Match, Red = Significant Mismatch)
        heatmap = cv2.applyColorMap(norm_diff, cv2.COLORMAP_JET)

        # Alpha blend: 65% original, 35% heatmap
        blended = cv2.addWeighted(scan_crop_bgr, 0.65, heatmap, 0.35, 0)

        # Detect salient anomaly blobs for bounding box annotations
        _, thresh = cv2.threshold(norm_diff, 180, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            area = bw * bh
            if area > (w * h * 0.02):  # Minimum 2% of area
                diff_score = float(np.mean(norm_diff[y:y+bh, x:x+bw]) / 255.0)
                regions.append(RegionBox(
                    x_min=round(float(x / w), 3),
                    y_min=round(float(y / h), 3),
                    x_max=round(float((x + bw) / w), 3),
                    y_max=round(float((y + bh) / h), 3),
                    label="Visual Anomaly Zone",
                    difference_score=round(diff_score, 3),
                    explanation=f"Packaging surface deviates from reference pattern with difference magnitude {round(diff_score * 100, 1)}%."
                ))

        return blended, regions


class ExplanationEngine:
    """
    Synthesizes grounded, evidence-backed narrative explanation from the full verification pipeline.
    """
    @staticmethod
    def generate_narrative(
        decision: DecisionResult,
        evidences: list[EvidenceObject],
        product_name: str,
        packaging_version: str
    ) -> str:
        supporting: list[str] = []
        contradictory: list[str] = []

        for ev in evidences:
            if not ev.availability or ev.score is None:
                continue
            if ev.score >= 0.75:
                supporting.append(f"{ev.type.value.capitalize()} matches registered specifications ({round(ev.score * 100)}%)")
            elif ev.score <= 0.45:
                contradictory.append(f"{ev.type.value.capitalize()} deviates from reference standard ({round(ev.score * 100)}%)")

        narrative_parts = [
            f"VeriSure AI conducted a multi-evidence risk assessment for '{product_name}' (Packaging Version: {packaging_version}).",
            f"Decision State: {decision.state.value} with Risk Score of {decision.risk_score}/100 and Confidence of {round(decision.confidence * 100, 1)}%."
        ]

        if supporting:
            narrative_parts.append(f"Strongest supporting markers: {', '.join(supporting[:3])}.")

        if contradictory:
            narrative_parts.append(f"Cautionary deviations noted: {', '.join(contradictory[:3])}.")

        if decision.contradictions:
            narrative_parts.append(f"Identified Contradictions: {decision.contradictions[0]}")

        narrative_parts.append(f"Recommended Consumer Action: {decision.recommendation}")
        narrative_parts.append("Important Disclaimer: A photograph cannot guarantee chemical or biological contents inside sealed packaging. This assessment represents visual, textual, and machine-readable conformity only.")

        return " ".join(narrative_parts)
