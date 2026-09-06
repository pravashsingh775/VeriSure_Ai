import re
from typing import Any

import cv2
import numpy as np


class VariantValidator:
    """
    Multi-signal variant validator for Amul Gold, Amul Taaza, and Amul Shakti.
    Strictly prevents false associations and never trusts filename alone.
    Explicitly categorizes competitor brands as OTHER_BRAND and diagrams as NON_PRODUCT_IMAGE.
    """

    COMPETITOR_BRANDS = [
        "mother dairy", "nandini", "country delight", "nestle", "gokul",
        "saras", "verka", "sudha", "aavin", "heritage", "vijaya", "dodla", "milma"
    ]

    DIAGRAM_KEYWORDS = [
        "architecture", "system", "component", "diagram", "database",
        "api", "infrastructure", "uml", "flowchart", "wireframe", "schema"
    ]

    BARCODE_MAP = {
        "8901262260114": "AMUL_GOLD",
        "8901262150217": "AMUL_GOLD",
        "8901262260091": "AMUL_TAAZA",
        "8901262150316": "AMUL_TAAZA",
        "8901262260138": "AMUL_SHAKTI",
        "8901262150415": "AMUL_SHAKTI",
    }

    def validate(
        self,
        img_bgr: np.ndarray,
        ocr_text: str = "",
        barcode: str | None = None,
        source_url: str = ""
    ) -> tuple[str, float, dict[str, Any]]:
        """
        Determines product variant using multi-signal fusion.
        Returns (variant_class, confidence, signal_breakdown).
        """
        text_lower = ocr_text.lower()
        signals: dict[str, Any] = {
            "barcode_match": None,
            "text_matches": {},
            "color_signature": None,
            "detected_competitor": None,
            "is_diagram": False
        }

        # 1. Competitor Brand Check -> OTHER_BRAND
        for competitor in self.COMPETITOR_BRANDS:
            if competitor in text_lower:
                signals["detected_competitor"] = competitor
                return "OTHER_BRAND", 0.99, signals

        # 2. Non-Product Graphic / Diagram Check -> NON_PRODUCT_IMAGE
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        white_pixels = np.sum(gray > 240) / gray.size
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.mean(edges > 0))
        diagram_hit_count = sum(1 for kw in self.DIAGRAM_KEYWORDS if kw in text_lower)

        if (white_pixels > 0.82 and edge_density > 0.08) or diagram_hit_count >= 2:
            signals["is_diagram"] = True
            return "NON_PRODUCT_IMAGE", 0.95, signals

        # Variant scores
        scores = {"AMUL_GOLD": 0.0, "AMUL_TAAZA": 0.0, "AMUL_SHAKTI": 0.0}

        # 3. Barcode Signal (High Weight: 0.45)
        if barcode:
            clean_bc = re.sub(r"\D", "", barcode)
            matched_variant = self.BARCODE_MAP.get(clean_bc)
            if matched_variant:
                scores[matched_variant] += 0.45
                signals["barcode_match"] = matched_variant

        # 4. Text / OCR Tokens Signal (Weight up to 0.45)
        # Gold
        gold_tokens = ["gold", "full cream", "गोल्ड", "6.0% fat", "6.0 %", "6.0%"]
        gold_hits = [t for t in gold_tokens if t in text_lower]
        if gold_hits:
            scores["AMUL_GOLD"] += min(0.45, 0.25 + 0.10 * len(gold_hits))
            signals["text_matches"]["AMUL_GOLD"] = gold_hits

        # Taaza
        taaza_tokens = ["taaza", "taza", "toned milk", "ताज़ा", "ताजा", "3.0% fat", "3.0 %", "3.0%"]
        taaza_hits = [t for t in taaza_tokens if t in text_lower]
        if taaza_hits:
            scores["AMUL_TAAZA"] += min(0.45, 0.25 + 0.10 * len(taaza_hits))
            signals["text_matches"]["AMUL_TAAZA"] = taaza_hits

        # Shakti
        shakti_tokens = ["shakti", "standardised", "standardized", "शक्ति", "4.5% fat", "4.5 %", "4.5%"]
        shakti_hits = [t for t in shakti_tokens if t in text_lower]
        if shakti_hits:
            scores["AMUL_SHAKTI"] += min(0.45, 0.25 + 0.10 * len(shakti_hits))
            signals["text_matches"]["AMUL_SHAKTI"] = shakti_hits

        # 5. Color Palette Signature Signal (Weight up to 0.20)
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        h_channel = hsv[:, :, 0]
        s_channel = hsv[:, :, 1]
        v_channel = hsv[:, :, 2]
        sat_mask = (s_channel > 50) & (v_channel > 40)

        if np.sum(sat_mask) > 1000:
            filtered_h = h_channel[sat_mask]
            # Gold red: H in [0, 15] or [165, 180]
            red_ratio = float(np.sum((filtered_h <= 15) | (filtered_h >= 165)) / filtered_h.size)
            # Taaza blue: H in [90, 130]
            blue_ratio = float(np.sum((filtered_h >= 90) & (filtered_h <= 130)) / filtered_h.size)
            # Shakti green: H in [35, 85]
            green_ratio = float(np.sum((filtered_h >= 35) & (filtered_h <= 85)) / filtered_h.size)

            signals["color_signature"] = {
                "red_ratio": round(red_ratio, 3),
                "blue_ratio": round(blue_ratio, 3),
                "green_ratio": round(green_ratio, 3)
            }

            if red_ratio > 0.22:
                scores["AMUL_GOLD"] += 0.20
            elif blue_ratio > 0.22:
                scores["AMUL_TAAZA"] += 0.20
            elif green_ratio > 0.22:
                scores["AMUL_SHAKTI"] += 0.20

        # Consensus Evaluation
        best_variant, best_score = max(scores.items(), key=lambda x: x[1])

        # Enforce minimum consensus threshold
        if best_score >= 0.40:
            # Check for close contradiction
            sorted_scores = sorted(scores.values(), reverse=True)
            if len(sorted_scores) > 1 and sorted_scores[0] - sorted_scores[1] < 0.10 and sorted_scores[1] > 0.35:
                # Contradiction between signals
                return "UNKNOWN", 0.30, signals

            return best_variant, round(min(0.99, best_score), 2), signals

        return "UNKNOWN", 0.20, signals

