import cv2
import numpy as np
from typing import Tuple
from backend.app.ai.contracts import BaseProductDetector, DetectedProductBox


class ProductDetector(BaseProductDetector):
    """
    Locates the product packaging boundary and isolates the object from the background.
    """
    def detect(self, image_bgr: np.ndarray) -> Tuple[DetectedProductBox, np.ndarray]:
        h, w = image_bgr.shape[:2]
        if h == 0 or w == 0:
            return DetectedProductBox(bbox=(0.0, 0.0, 1.0, 1.0), confidence=0.0, aspect_ratio=1.0), image_bgr

        # 1. Grayscale & Gaussian blur to suppress fine surface texture
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # 2. Canny Edge + Morphological Close to connect boundary lines
        edges = cv2.Canny(blurred, 30, 120)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        # 3. Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_bbox = (0, 0, w, h)
        best_cnt = None
        max_area = 0
        img_area = h * w

        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            area = bw * bh
            # Filter tiny background noise or extreme aspect ratio slivers
            if area > img_area * 0.12 and area > max_area:
                aspect = bh / max(1, bw)
                if 0.4 <= aspect <= 3.5:  # Realistic pouch / carton aspect ratios
                    max_area = area
                    best_bbox = (x, y, bw, bh)
                    best_cnt = cnt

        x, y, bw, bh = best_bbox
        # Add a gentle 3% safety margin around bbox
        pad_x = int(bw * 0.03)
        pad_y = int(bh * 0.03)
        x_min = max(0, x - pad_x)
        y_min = max(0, y - pad_y)
        x_max = min(w, x + bw + pad_x)
        y_max = min(h, y + bh + pad_y)

        # Normalized coordinates (ymin, xmin, ymax, xmax)
        norm_bbox = (
            float(y_min / h),
            float(x_min / w),
            float(y_max / h),
            float(x_max / w)
        )
        # Build contour mask around packaging to suppress background bleed (tables, hands, tiles)
        if best_cnt is not None and max_area < (img_area * 0.95):
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(mask, [best_cnt], -1, 255, thickness=cv2.FILLED)
            # Dilate mask gently to preserve peripheral print details
            mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)), iterations=1)
            # Mask out background by blending non-pouch pixels into neutral white
            isolated_bgr = image_bgr.copy()
            isolated_bgr[mask == 0] = (255, 255, 255)
            cropped = isolated_bgr[y_min:y_max, x_min:x_max]
        else:
            cropped = image_bgr[y_min:y_max, x_min:x_max]

        cropped = image_bgr[y_min:y_max, x_min:x_max]
        if cropped.size == 0:
            cropped = image_bgr
            norm_bbox = (0.0, 0.0, 1.0, 1.0)
        else:
            # Normalized coordinates (ymin, xmin, ymax, xmax)
            norm_bbox = (
                float(y_min / h),
                float(x_min / w),
                float(y_max / h),
                float(x_max / w)
            )

        detected_area = (x_max - x_min) * (y_max - y_min)
        confidence = float(np.clip(detected_area / img_area, 0.5, 0.98))
        aspect_ratio = float((y_max - y_min) / max(1, (x_max - x_min)))

        box_result = DetectedProductBox(
            bbox=norm_bbox,
            confidence=round(confidence, 3),
            aspect_ratio=round(aspect_ratio, 3)
        )
        return box_result, cropped
