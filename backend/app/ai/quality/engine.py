
import cv2
import numpy as np

from backend.app.ai.contracts import BaseImageQualityEngine, QualityAssessmentResult


class ImageQualityEngine(BaseImageQualityEngine):
    """
    Evaluates physical capture quality before downstream AI inference.
    Prevents false certainty and outputs actionable recapture guidance when unusable.
    """
    def assess(self, image_bgr: np.ndarray) -> QualityAssessmentResult:
        if image_bgr is None or image_bgr.size == 0:
            return QualityAssessmentResult(
                resolution_score=0.0,
                blur_score=0.0,
                brightness_score=0.0,
                contrast_score=0.0,
                glare_score=0.0,
                occlusion_score=0.0,
                overall_quality=0.0,
                usable=False,
                reasons=["EMPTY_OR_CORRUPT_IMAGE"],
                guidance="Please provide a valid, readable product photograph."
            )

        h, w = image_bgr.shape[:2]
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Resolution Score (Target: at least 720p equivalent area)
        res_metric = np.sqrt(h * w)
        resolution_score = float(np.clip(res_metric / 720.0, 0.1, 1.0))

        # 2. Blur Score (Laplacian variance)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        # lap_var > 250 is very crisp; < 80 is blurry
        blur_score = float(np.clip(lap_var / 250.0, 0.05, 1.0))

        # 3. Brightness Score
        mean_brightness = float(gray.mean())
        # Ideal range is 70 - 200 (centered ~ 135)
        brightness_dist = abs(mean_brightness - 135.0)
        brightness_score = float(np.clip(1.0 - (brightness_dist / 120.0), 0.1, 1.0))

        # 4. Contrast Score (Standard deviation of intensity)
        std_contrast = float(gray.std())
        contrast_score = float(np.clip(std_contrast / 50.0, 0.1, 1.0))

        # 5. Glare Score (Specular blown-out highlights)
        # In milk packaging, white polyethylene (Value > 250, Saturation < 15) is the primary material!
        # True specular glare is characterized by extreme brightness clipping (all channels >= 253)
        # with flat gradient variance.
        b_ch, g_ch, r_ch = cv2.split(image_bgr)
        clipped_specular = (b_ch >= 253) & (g_ch >= 253) & (r_ch >= 253)
        glare_ratio = float(np.sum(clipped_specular) / (h * w))
        # Glare score reflects highlight proportion
        glare_score = float(np.clip(1.0 - (glare_ratio * 2.0), 0.2, 1.0))

        # 6. Occlusion / Framing Check (Border edge density)
        border_thickness = max(2, int(min(h, w) * 0.02))
        top_edge = np.mean(cv2.Canny(gray[:border_thickness, :], 50, 150) > 0)
        bot_edge = np.mean(cv2.Canny(gray[h-border_thickness:, :], 50, 150) > 0)
        border_edge_activity = (top_edge + bot_edge) / 2.0
        occlusion_score = float(np.clip(1.0 - (border_edge_activity * 2.0), 0.2, 1.0))

        # Weighted Overall Quality
        overall = (
            0.30 * blur_score +
            0.25 * glare_score +
            0.20 * contrast_score +
            0.15 * brightness_score +
            0.10 * resolution_score
        )
        overall_quality = float(np.clip(overall, 0.0, 1.0))

        # Usability determination & reason codes
        reasons: list[str] = []
        guidance_parts: list[str] = []

        # Fatal defects that prevent accurate feature extraction
        if blur_score < 0.20:
            reasons.append("HIGH_MOTION_BLUR")
            guidance_parts.append("Hold the camera steady and wait for focus.")
        if mean_brightness < 30:
            reasons.append("UNDEREXPOSED_DARK")
            guidance_parts.append("Increase surrounding lighting or use flashlight.")
        elif mean_brightness > 252 and contrast_score < 0.20:
            reasons.append("OVEREXPOSED_WASHOUT")
            guidance_parts.append("Reduce direct harsh light on the package.")
        if glare_ratio > 0.55:
            reasons.append("HARSH_PACKAGING_GLARE")
            guidance_parts.append("Tilt the camera slightly to avoid direct reflective glare.")
        if resolution_score < 0.15:
            reasons.append("LOW_IMAGE_RESOLUTION")
            guidance_parts.append("Move closer to fill the frame with the product.")

        usable = len(reasons) == 0 and overall_quality >= 0.25
        guidance = " ".join(guidance_parts) if guidance_parts else "Image quality is sufficient for authentic feature extraction."

        return QualityAssessmentResult(
            resolution_score=round(resolution_score, 3),
            blur_score=round(blur_score, 3),
            brightness_score=round(brightness_score, 3),
            contrast_score=round(contrast_score, 3),
            glare_score=round(glare_score, 3),
            occlusion_score=round(occlusion_score, 3),
            overall_quality=round(overall_quality, 3),
            usable=usable,
            reasons=reasons,
            guidance=guidance
        )
