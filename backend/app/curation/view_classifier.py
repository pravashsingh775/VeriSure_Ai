import re
from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np


class PackagingViewClassifier:
    """
    Classifies packaging images into canonical views:
    FRONT, BACK, SIDE, TOP, BOTTOM, SEAL, BARCODE, QR, NUTRITION, DATE_MRP, DETAIL, UNKNOWN.
    """

    NUTRITION_KEYWORDS = [
        "nutritional information", "nutrition facts", "per 100", "energy kcal",
        "total fat", "protein", "carbohydrate", "added sugar", "calcium"
    ]

    DATE_MRP_KEYWORDS = [
        "mrp", "use by", "mfd", "pkg date", "batch no", "lot no", "mfg date", "best before"
    ]

    BACK_PANEL_KEYWORDS = [
        "marketed by", "manufactured by", "fssai", "lic no", "consumer care",
        "gcmmf", "recycle", "anand", "net content", "unit code"
    ]

    FRONT_PANEL_KEYWORDS = [
        "full cream milk", "toned milk", "standardised milk", "standardized milk",
        "rich & creamy", "fresh & pure", "pasteurised", "pasteurized"
    ]

    def classify_view(
        self,
        img_bgr: np.ndarray,
        ocr_text: str = "",
        barcode_detected: bool = False,
        qr_detected: bool = False,
        barcode_area_ratio: float = 0.0,
        qr_area_ratio: float = 0.0
    ) -> Tuple[str, float]:
        """
        Classifies view angle and returns (view_type, confidence).
        """
        h, w = img_bgr.shape[:2]
        aspect_ratio = w / float(h)
        text_lower = ocr_text.lower()

        # 1. Macro Barcode View
        if barcode_detected and barcode_area_ratio > 0.30:
            return "BARCODE", 0.95

        # 2. Macro QR View
        if qr_detected and qr_area_ratio > 0.30:
            return "QR", 0.95

        # 3. Macro Seal / Crimp View (Extremely wide or high aspect ratio on crimp pattern)
        if (aspect_ratio > 3.0 or aspect_ratio < 0.33) and len(text_lower.strip()) < 15:
            # Check edge periodicity or horizontal gradient
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            edge_var = float(cv2.Sobel(gray, cv2.CV_64F, 1, 0).var())
            if edge_var > 400:
                return "SEAL", 0.85

        # 4. Nutrition Macro View
        nutrition_hits = sum(1 for kw in self.NUTRITION_KEYWORDS if kw in text_lower)
        if nutrition_hits >= 3 and not barcode_detected and len(text_lower) < 300:
            return "NUTRITION", 0.90

        # 5. Date / MRP Macro View
        date_hits = sum(1 for kw in self.DATE_MRP_KEYWORDS if kw in text_lower)
        if date_hits >= 2 and len(text_lower) < 150 and not barcode_detected:
            return "DATE_MRP", 0.85

        # 6. Back Panel Evaluation
        back_hits = sum(1 for kw in self.BACK_PANEL_KEYWORDS if kw in text_lower)
        back_score = 0.0

        if barcode_detected:
            back_score += 0.45
        if back_hits >= 2:
            back_score += 0.35
        if nutrition_hits >= 2:
            back_score += 0.25
        if "fssai" in text_lower or "10012021000071" in text_lower:
            back_score += 0.20

        # 7. Front Panel Evaluation
        front_hits = sum(1 for kw in self.FRONT_PANEL_KEYWORDS if kw in text_lower)
        front_score = 0.0

        # Front typically has large bold typography, prominent logo, but no barcode
        if not barcode_detected:
            front_score += 0.30
        if front_hits >= 1:
            front_score += 0.40
        if "amul" in text_lower and ("gold" in text_lower or "taaza" in text_lower or "shakti" in text_lower):
            front_score += 0.30
        if back_hits == 0 and nutrition_hits == 0:
            front_score += 0.20

        # Decision Logic
        if back_score >= 0.55 and back_score > front_score:
            conf = min(0.98, back_score)
            return "BACK", round(conf, 2)

        if front_score >= 0.50:
            conf = min(0.95, front_score)
            return "FRONT", round(conf, 2)

        # 8. Detail View (Macro crop of packaging text, logo badge, or storage instruction)
        if len(text_lower.strip()) > 20 and min(w, h) < 400:
            return "DETAIL", 0.75

        # 9. Fallback if inconclusive
        if barcode_detected:
            return "BACK", 0.65

        if "amul" in text_lower:
            return "FRONT", 0.60

        return "UNKNOWN", 0.40

