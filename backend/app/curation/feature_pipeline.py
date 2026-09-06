from typing import Any

import cv2
import numpy as np

from backend.app.ai.certification.engine import CertificationAnalyzer
from backend.app.ai.codes.barcode import BarcodeAnalyzer
from backend.app.ai.codes.qr import QRAnalyzer
from backend.app.ai.ocr.engine import OCREngine
from backend.app.ai.quality.engine import ImageQualityEngine
from backend.app.ai.vision.colour import ColourAnalyzer
from backend.app.ai.vision.layout import LayoutAnalyzer
from backend.app.ai.vision.logo import LogoAnalyzer
from backend.app.ai.vision.print import PrintQualityAnalyzer
from backend.app.ai.vision.seal import SealAnalyzer
from backend.app.ai.vision.shape import ShapeAnalyzer
from backend.app.ai.vision.texture import TextureAnalyzer
from backend.app.ai.vision.typography import TypographyAnalyzer


class ReferenceFeatureExtractionPipeline:
    """
    Automated feature extraction pipeline utilizing the 12 VeriSure AI evidence engines.
    Produces clean, structured, interpretable packaging fingerprints for reference corpus V2.
    """

    def __init__(self):
        self.quality_engine = ImageQualityEngine()
        self.logo_analyzer = LogoAnalyzer()
        self.layout_analyzer = LayoutAnalyzer()
        self.colour_analyzer = ColourAnalyzer()
        self.typography_analyzer = TypographyAnalyzer()
        self.texture_analyzer = TextureAnalyzer()
        self.shape_analyzer = ShapeAnalyzer()
        self.seal_analyzer = SealAnalyzer()
        self.print_analyzer = PrintQualityAnalyzer()
        self.ocr_engine = OCREngine()
        self.barcode_analyzer = BarcodeAnalyzer()
        self.qr_analyzer = QRAnalyzer()
        self.cert_analyzer = CertificationAnalyzer()

    def extract_reference_features(
        self,
        img_bgr: np.ndarray,
        variant: str,
        packaging_version: str = "V2",
        view_type: str = "FRONT",
        reference_metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Executes all 12 analyzers on an approved packaging reference image
        and constructs a structured packaging fingerprint.
        """
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Quality Assessment
        qual_res = self.quality_engine.assess(img_bgr)

        # 2. Logo Features
        logo_ev = self.logo_analyzer.analyze(img_bgr, None, reference_metadata)
        logo_features = logo_ev.features or {}
        # Also extract intrinsic ORB keypoints for reference database indexing
        orb = cv2.ORB_create(nfeatures=500)
        kps, des = orb.detectAndCompute(gray, None)
        logo_features["orb_keypoint_count"] = len(kps)
        logo_features["has_descriptors"] = des is not None and len(des) > 0

        # 3. Layout Features
        layout_ev = self.layout_analyzer.analyze(img_bgr, None, reference_metadata)
        layout_features = layout_ev.features or {}
        # Centroid and spatial mass
        moments = cv2.moments(gray)
        if moments["m00"] > 0:
            cx = float(moments["m10"] / moments["m00"])
            cy = float(moments["m01"] / moments["m00"])
            layout_features["centroid_norm"] = [round(cx / w, 3), round(cy / h, 3)]

        # 4. Colour Features (LAB palette & HSV summary)
        colour_ev = self.colour_analyzer.analyze(img_bgr, None, reference_metadata)
        colour_features = colour_ev.features or {}
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        mean_hsv = cv2.mean(hsv)[:3]
        colour_features["mean_hsv"] = [round(float(x), 2) for x in mean_hsv]

        # 5. Typography Features
        typo_ev = self.typography_analyzer.analyze(img_bgr, None, reference_metadata)
        typo_features = typo_ev.features or {}

        # 6. Texture Features
        texture_ev = self.texture_analyzer.analyze(img_bgr, None, reference_metadata)
        texture_features = texture_ev.features or {}
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        texture_features["laplacian_variance"] = round(lap_var, 2)

        # 7. Shape Features
        shape_ev = self.shape_analyzer.analyze(img_bgr, None, reference_metadata)
        shape_features = shape_ev.features or {}

        # 8. Seal Features
        seal_ev = self.seal_analyzer.analyze(img_bgr, None, reference_metadata)
        seal_features = {
            "available": seal_ev.availability,
            "crimp_integrity_score": seal_ev.score,
            "explanation": seal_ev.explanation
        }

        # 9. Print Quality Features
        print_ev = self.print_analyzer.analyze(img_bgr, None, reference_metadata)
        print_features = print_ev.features or {}
        print_features["acuity_score"] = print_ev.score

        # 10. OCR Engine Text Extraction & Field Parsing
        raw_text, ocr_conf, ocr_regions = self.ocr_engine.extract_text(img_bgr)
        ocr_features = {
            "extracted_text_excerpt": raw_text[:200].replace("\n", " ") if raw_text else "",
            "confidence": round(ocr_conf, 3),
            "total_characters": len(raw_text)
        }

        # 11. Barcode Decoding
        barcode_ev = self.barcode_analyzer.analyze(img_bgr)
        barcode_features = {
            "available": barcode_ev.availability,
            "barcode_value": barcode_ev.features.get("decoded_value") if barcode_ev.availability else None,
            "barcode_type": barcode_ev.features.get("type", "EAN13") if barcode_ev.availability else None,
            "checksum_valid": barcode_ev.features.get("checksum_valid", False) if barcode_ev.availability else None,
            "confidence": barcode_ev.confidence
        }

        # 12. QR Decoding
        qr_ev = self.qr_analyzer.analyze(img_bgr)
        qr_features = {
            "available": qr_ev.availability,
            "qr_content": qr_ev.features.get("decoded_value") if qr_ev.availability else None,
            "domain": qr_ev.features.get("domain") if qr_ev.availability else None,
            "confidence": qr_ev.confidence
        }

        # 13. Regulatory / Certification Analysis (FSSAI)
        cert_ev = self.cert_analyzer.analyze(raw_text)
        cert_features = {
            "available": cert_ev.availability,
            "fssai_license": cert_ev.features.get("license_number") if cert_ev.availability else None,
            "syntax_valid": cert_ev.features.get("syntax_valid", False) if cert_ev.availability else None,
            "jurisdiction": cert_ev.features.get("state") if cert_ev.availability else None
        }

        # Construct Structured Fingerprint
        fingerprint = {
            "variant": variant,
            "packaging_version": packaging_version,
            "view": view_type,
            "dimensions": f"{w}x{h}",
            "quality": {
                "overall_quality": round(qual_res.overall_quality, 3),
                "usable": qual_res.usable,
                "blur_score": round(qual_res.blur_score, 3)
            },
            "logo_features": logo_features,
            "layout_features": layout_features,
            "colour_features": colour_features,
            "typography_features": typo_features,
            "texture_features": texture_features,
            "shape_features": shape_features,
            "seal_features": seal_features,
            "print_features": print_features,
            "ocr_features": ocr_features,
            "barcode_features": barcode_features,
            "qr_features": qr_features,
            "certification_features": cert_features
        }

        return {
            "fingerprint": fingerprint,
            "individual_features": {
                "QUALITY": fingerprint["quality"],
                "LOGO": logo_features,
                "LAYOUT": layout_features,
                "COLOR_PALETTE": colour_features,
                "TYPOGRAPHY": typo_features,
                "TEXTURE_LBP": texture_features,
                "SHAPE": shape_features,
                "SEAL": seal_features,
                "PRINT": print_features,
                "OCR": ocr_features,
                "BARCODE": barcode_features,
                "QR": qr_features,
                "CERTIFICATION": cert_features
            }
        }

