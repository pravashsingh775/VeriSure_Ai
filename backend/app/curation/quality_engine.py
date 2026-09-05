from dataclasses import asdict, dataclass
from typing import Any, Dict, Tuple
import cv2
import numpy as np


@dataclass
class QualityMetrics10D:
    width: int
    height: int
    resolution_score: float
    blur_score: float
    sharpness_score: float
    brightness_score: float
    contrast_score: float
    saturation_score: float
    exposure_score: float
    glare_score: float
    compression_score: float
    text_readability_score: float
    overall_quality: float
    quality_status: str  # EXCELLENT, GOOD, ACCEPTABLE, POOR, REJECT
    usable: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PackagingQualityEngine10D:
    """
    10-Dimension Scientific Image Quality Grader for Consumer Packaging.
    Evaluates resolution, blur, sharpness, brightness, contrast, saturation,
    exposure clipping, specular glare, compression artifacts, and text readability.
    """

    def __init__(
        self,
        min_dim_threshold: int = 250,
        blur_var_threshold: float = 80.0,
        rejection_threshold: float = 0.30
    ):
        self.min_dim_threshold = min_dim_threshold
        self.blur_var_threshold = blur_var_threshold
        self.rejection_threshold = rejection_threshold

    def evaluate(self, img_bgr: np.ndarray) -> QualityMetrics10D:
        """Evaluates all 10 visual quality dimensions on a BGR image array."""
        h, w = img_bgr.shape[:2]

        # 1. Resolution Score
        min_dim = min(h, w)
        if min_dim < self.min_dim_threshold:
            res_score = max(0.05, min_dim / self.min_dim_threshold * 0.4)
        elif min_dim >= 800:
            res_score = 1.0
        else:
            res_score = 0.4 + (min_dim - self.min_dim_threshold) / (800 - self.min_dim_threshold) * 0.6
        res_score = round(float(np.clip(res_score, 0.0, 1.0)), 3)

        # Grayscale conversions on scale-normalized representation for invariant gradient metrics
        max_dim = max(h, w)
        if max_dim > 1000:
            scale = 1000.0 / max_dim
            eval_img = cv2.resize(img_bgr, (int(w * scale), int(h * scale)))
        else:
            eval_img = img_bgr

        gray = cv2.cvtColor(eval_img, cv2.COLOR_BGR2GRAY)

        # 2. Blur Score (Scale-invariant Laplacian variance)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        blur_score = round(float(np.clip(lap_var / 300.0, 0.0, 1.0)), 3)

        # 3. Sharpness Score (Tenengrad Sobel magnitude)
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        tenengrad = float(np.mean(np.sqrt(gx**2 + gy**2)))
        sharpness_score = round(float(np.clip(tenengrad / 35.0, 0.0, 1.0)), 3)

        # HSV conversions
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        h_ch, s_ch, v_ch = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

        # 4. Brightness Score (Optimal V mean between 110 and 190)
        mean_v = float(np.mean(v_ch))
        if 110 <= mean_v <= 190:
            brightness_score = 1.0
        elif mean_v < 110:
            brightness_score = max(0.0, mean_v / 110.0)
        else:
            brightness_score = max(0.0, (255.0 - mean_v) / 65.0)
        brightness_score = round(float(np.clip(brightness_score, 0.0, 1.0)), 3)

        # 5. Contrast Score (RMS contrast normalized)
        rms_contrast = float(np.std(gray) / 255.0)
        # Optimal contrast between 0.18 and 0.40
        if 0.18 <= rms_contrast <= 0.40:
            contrast_score = 1.0
        elif rms_contrast < 0.18:
            contrast_score = rms_contrast / 0.18
        else:
            contrast_score = max(0.0, (0.60 - rms_contrast) / 0.20)
        contrast_score = round(float(np.clip(contrast_score, 0.0, 1.0)), 3)

        # 6. Saturation Score (Mean S channel)
        mean_s = float(np.mean(s_ch))
        # Packaging colors typically have mean S between 25 and 180
        if 30 <= mean_s <= 180:
            saturation_score = 1.0
        elif mean_s < 30:
            saturation_score = max(0.2, mean_s / 30.0)
        else:
            saturation_score = max(0.4, (255.0 - mean_s) / 75.0)
        saturation_score = round(float(np.clip(saturation_score, 0.0, 1.0)), 3)

        # 7. Exposure Score (Clipping at extremes: v < 5 or v > 250)
        clipped_dark = np.sum(v_ch <= 5) / v_ch.size
        clipped_bright = np.sum(v_ch >= 250) / v_ch.size
        total_clipping = float(clipped_dark + clipped_bright)
        exposure_score = round(float(np.clip(1.0 - (total_clipping * 3.0), 0.0, 1.0)), 3)

        # 8. Glare Score (Specular reflections: very bright and desaturated)
        glare_mask = (v_ch > 248) & (s_ch < 30)
        glare_ratio = float(np.sum(glare_mask) / v_ch.size)
        glare_score = round(float(np.clip(1.0 - (glare_ratio * 6.0), 0.0, 1.0)), 3)

        # 9. Compression Artifacts Score (Blocking artifact measure across 8x8 grids)
        if w >= 16:
            c7 = gray[:, 7::8].astype(np.float32)
            c8 = gray[:, 8::8].astype(np.float32)
            min_h = min(c7.shape[1], c8.shape[1])
            diff_h = np.abs(c7[:, :min_h] - c8[:, :min_h]) if min_h > 0 else 0

            c3 = gray[:, 3::8].astype(np.float32)
            c4 = gray[:, 4::8].astype(np.float32)
            min_intra = min(c3.shape[1], c4.shape[1])
            diff_intra = np.abs(c3[:, :min_intra] - c4[:, :min_intra]) if min_intra > 0 else 0
        else:
            diff_h = 0
            diff_intra = 0

        mean_boundary = float(np.mean(diff_h)) if isinstance(diff_h, np.ndarray) and diff_h.size > 0 else 0.0
        mean_intra = float(np.mean(diff_intra)) if isinstance(diff_intra, np.ndarray) and diff_intra.size > 0 else 1.0
        blocking_ratio = max(0.0, (mean_boundary - mean_intra) / (mean_intra + 1e-5))
        compression_score = round(float(np.clip(1.0 - (blocking_ratio * 0.4), 0.2, 1.0)), 3)

        # 10. Text Readability / High-Frequency Edge Density
        edges = cv2.Canny(gray, 70, 150)
        edge_density = float(np.mean(edges > 0))
        # Packaging text yields edge density around 0.03 - 0.15
        if 0.03 <= edge_density <= 0.18:
            readability_score = 1.0
        elif edge_density < 0.03:
            readability_score = max(0.2, edge_density / 0.03)
        else:
            readability_score = max(0.5, (0.35 - edge_density) / 0.17)
        readability_score = round(float(np.clip(readability_score, 0.0, 1.0)), 3)

        # Weighted Combination
        weights = {
            "res": 0.15,
            "blur": 0.20,
            "sharp": 0.10,
            "bright": 0.10,
            "contrast": 0.15,
            "sat": 0.05,
            "exp": 0.08,
            "glare": 0.07,
            "comp": 0.05,
            "read": 0.05
        }

        overall = (
            res_score * weights["res"]
            + blur_score * weights["blur"]
            + sharpness_score * weights["sharp"]
            + brightness_score * weights["bright"]
            + contrast_score * weights["contrast"]
            + saturation_score * weights["sat"]
            + exposure_score * weights["exp"]
            + glare_score * weights["glare"]
            + compression_score * weights["comp"]
            + readability_score * weights["read"]
        )
        overall = round(float(np.clip(overall, 0.0, 1.0)), 3)

        # Categorical Status
        if overall >= 0.80:
            status = "EXCELLENT"
        elif overall >= 0.65:
            status = "GOOD"
        elif overall >= 0.50:
            status = "ACCEPTABLE"
        elif overall >= self.rejection_threshold:
            status = "POOR"
        else:
            status = "REJECT"

        usable = (overall >= 0.45) and (min_dim >= 200) and (blur_score >= 0.05 or lap_var >= 25.0)

        return QualityMetrics10D(
            width=w,
            height=h,
            resolution_score=res_score,
            blur_score=blur_score,
            sharpness_score=sharpness_score,
            brightness_score=brightness_score,
            contrast_score=contrast_score,
            saturation_score=saturation_score,
            exposure_score=exposure_score,
            glare_score=glare_score,
            compression_score=compression_score,
            text_readability_score=readability_score,
            overall_quality=overall,
            quality_status=status,
            usable=usable
        )

