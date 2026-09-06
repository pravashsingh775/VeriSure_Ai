import re
from typing import Any

import cv2
import numpy as np

from backend.app.ai.contracts import EvidenceObject, EvidenceType, RegionBox


class StructuredOCRParser:
    """
    Extracts and validates structured FMCG packaging fields according to Indian Dairy regulations.
    """
    PATTERNS = {
        "mrp": r"(?:MRP|Rs\.?|₹|PRICE)\s*[:\.]?\s*([0-9]+(?:\.[0-9]{2})?)",
        "fssai": r"(?:FSSAI|Lic\.?\s*No\.?|Licence\s*No\.?)\s*[:\.]?\s*([0-9]{14})",
        "batch": r"(?:BATCH|LOT|B\.?\s*NO\.?|BN)\s*[:\.]?\s*([A-Z0-9\/\-]+)",
        "net_qty": r"([0-9]+(?:\.[0-9]+)?\s*(?:ml|mL|L|litres?|g|kg))",
        "mfd_date": r"(?:MFD|PKD|PACKED|MFG)\s*[:\.]?\s*([0-9]{2}[\/\.\-][0-9]{2}[\/\.\-][0-9]{2,4})",
        "exp_date": r"(?:EXP|USE\s*BY|BEST\s*BEFORE|EXPIRY)\s*[:\.]?\s*([0-9]{2}[\/\.\-][0-9]{2}[\/\.\-][0-9]{2,4})",
    }

    @staticmethod
    def parse(raw_text: str) -> dict[str, Any]:
        extracted: dict[str, Any] = {}
        for key, pattern in StructuredOCRParser.PATTERNS.items():
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                extracted[key] = match.group(1).strip()
            else:
                extracted[key] = None

        # Check for brand mentions (English and Hindi)
        if re.search(r"\b(AMUL|अमूल)\b", raw_text, re.IGNORECASE):
            extracted["brand"] = "AMUL"
        else:
            extracted["brand"] = None

        # Product variant keywords (English and Devanagari Hindi)
        if re.search(r"\b(TAAZA|ताजा)\b", raw_text, re.IGNORECASE):
            extracted["detected_variant"] = "Taaza"
        elif re.search(r"\b(GOLD|गोल्ड)\b", raw_text, re.IGNORECASE):
            extracted["detected_variant"] = "Gold"
        elif re.search(r"\b(SHAKTI|शक्ति)\b", raw_text, re.IGNORECASE):
            extracted["detected_variant"] = "Shakti"
        elif re.search(r"\b(COW\s*MILK|गाय\s*का\s*दूध)\b", raw_text, re.IGNORECASE):
            extracted["detected_variant"] = "Cow Milk"
        else:
            extracted["detected_variant"] = None

        return extracted


class OCREngine:
    """
    Extracts text tokens and executes structured field recognition with internal consistency validation.
    """
    def __init__(self):
        self._easyocr_reader = None

    def _get_reader(self):
        if self._easyocr_reader is None:
            try:
                import os
                model_dir = os.path.expanduser("~/.EasyOCR/model")
                # Only initialize EasyOCR if weights are already cached locally to prevent blocking network hangs
                if os.path.exists(os.path.join(model_dir, "craft_mlt_25k.pth")) and os.path.exists(os.path.join(model_dir, "english_g2.pth")):
                    import easyocr
                    self._easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False, download_enabled=False)
                else:
                    self._easyocr_reader = False
            except Exception:
                self._easyocr_reader = False
        return self._easyocr_reader

    def extract_text(self, image_bgr: np.ndarray) -> tuple[str, float, list[dict[str, Any]]]:
        reader = self._get_reader()
        if reader:
            try:
                # Convert BGR to RGB for EasyOCR
                rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                # Enhance dot-matrix and low-contrast plastic printing using CLAHE on L-channel
                lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
                l_chan, a_chan, b_chan = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
                cl = clahe.apply(l_chan)
                enhanced_bgr = cv2.cvtColor(cv2.merge((cl, a_chan, b_chan)), cv2.COLOR_LAB2BGR)
                rgb = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB)
                results = reader.readtext(rgb)
                text_lines = []
                confidences = []
                box_details = []
                h, w = image_bgr.shape[:2]

                for bbox, text, conf in results:
                    text_lines.append(text)
                    confidences.append(conf)
                    # Normalize bbox
                    pts = np.array(bbox)
                    ymin = float(np.min(pts[:, 1]) / h)
                    xmin = float(np.min(pts[:, 0]) / w)
                    ymax = float(np.max(pts[:, 1]) / h)
                    xmax = float(np.max(pts[:, 0]) / w)
                    box_details.append({
                        "text": text,
                        "confidence": float(conf),
                        "bbox": (ymin, xmin, ymax, xmax)
                    })

                full_text = " ".join(text_lines)
                mean_conf = float(np.mean(confidences)) if confidences else 0.5
                return full_text, mean_conf, box_details
            except Exception:
                pass

        # Honest fallback: Empty result when OCR model or text is unavailable
        return "", 0.0, []

    def analyze(
        self,
        scan_crop_bgr: np.ndarray,
        reference_metadata: dict[str, Any] | None = None
    ) -> EvidenceObject:
        raw_text, ocr_conf, box_details = self.extract_text(scan_crop_bgr)
        if not raw_text or not raw_text.strip():
            return EvidenceObject(
                type=EvidenceType.OCR,
                score=None,
                confidence=0.0,
                availability=False,
                quality=0.50,
                source="verisure-ocr-structured-v1",
                features={
                    "raw_text": "",
                    "extracted_fields": {},
                    "detected_boxes_count": 0
                },
                regions=[],
                explanation="No readable text tokens detected or OCR engine unavailable.",
                warnings=["OCR_TEXT_NOT_DETECTED"]
            )

        extracted_fields = StructuredOCRParser.parse(raw_text)

        # Evaluate consistency with expected metadata
        expected_mrp = reference_metadata.get("expected_mrp") if reference_metadata else None
        expected_fssai = reference_metadata.get("expected_fssai") if reference_metadata else None

        score = 0.85
        warnings = []
        regions: list[RegionBox] = []

        if extracted_fields.get("brand") == "AMUL":
            score += 0.05

        if extracted_fields.get("fssai"):
            if expected_fssai and extracted_fields["fssai"] != expected_fssai:
                score -= 0.20
                warnings.append(f"Extracted FSSAI ({extracted_fields['fssai']}) does not match expected ({expected_fssai}).")
            else:
                score += 0.05

        if extracted_fields.get("mrp") and expected_mrp:
            try:
                mrp_val = float(extracted_fields["mrp"])
                if abs(mrp_val - float(expected_mrp)) > 5.0:
                    warnings.append(f"Extracted MRP (₹{mrp_val}) deviates from standard catalog MRP (₹{expected_mrp}).")
                    score -= 0.10
            except ValueError:
                pass

        score = float(np.clip(score, 0.20, 0.98))

        explanation = (
            f"Structured packaging text extraction completed with OCR confidence {round(ocr_conf * 100, 1)}%. "
            f"Brand: {extracted_fields.get('brand') or 'Not isolated'}, "
            f"FSSAI: {extracted_fields.get('fssai') or 'Not isolated'}, "
            f"MRP: {extracted_fields.get('mrp') or 'Not isolated'}."
        )

        return EvidenceObject(
            type=EvidenceType.OCR,
            score=round(score, 3),
            confidence=round(ocr_conf, 3),
            availability=bool(raw_text.strip()),
            quality=0.88,
            source="verisure-ocr-structured-v1",
            features={
                "raw_text": raw_text[:300],
                "extracted_fields": extracted_fields,
                "detected_boxes_count": len(box_details)
            },
            regions=regions,
            explanation=explanation,
            warnings=warnings
        )
