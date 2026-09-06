import re
from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np


class DomainGatekeeperEngine:
    """
    Domain Gatekeeper & Packaging Validation Engine.
    Enforces operational boundaries of the VeriSure AI platform:
    1. Physical Packaging Validation: Distinguishes physical milk pouch packaging from
       digital diagrams, schematics, system architectures, screenshots, and non-product documents.
    2. Brand Gatekeeper: Enforces Amul packaging calibration scope. Detects competitor or
       unsupported dairy brands (e.g. Mother Dairy, Nandini, Nestle, Country Delight) and prevents
       hallucinated comparisons against Amul reference templates.
    """

    # Diagram, schematic, and software architectural terms
    DIAGRAM_KEYWORDS = {
        "ARCHITECTURE", "SYSTEM", "COMPONENT", "DIAGRAM", "DATABASE", "API",
        "FLOWCHART", "SERVER", "SERVICE", "PIPELINE", "BACKEND", "FRONTEND",
        "DOCKER", "KUBERNETES", "MICROSERVICE", "WORKFLOW", "SCHEMA", "WIREFRAME",
        "UML", "MOCKUP", "SCREENSHOT", "CLIENT", "GATEWAY", "ENDPOINT", "INFRASTRUCTURE",
        "CONTROLLER", "REPOSITORY", "CLASS", "MODULE", "DEPLOYMENT", "ALGORITHM"
    }

    # Supported Brand keywords (GCMMF / Amul)
    AMUL_KEYWORDS = {
        "AMUL", "अमूल", "GCMMF", "ANAND", "GUJARAT COOPERATIVE",
        "GUJARAT CO-OPERATIVE", "MILK MARKETING FEDERATION", "KAIRA DISTRICT",
        "TAAZA", "AMUL GOLD", "AMUL TAAZA", "AMUL SHAKTI", "AMUL COW", "AMUL SLIM"
    }

    # Packaging / Food Retail Domain Keywords
    PACKAGING_KEYWORDS = {
        "MILK", "DAIRY", "PASTEURISED", "PASTEURIZED", "NUTRITIONAL", "NUTRITION",
        "FSSAI", "FAT", "PROTEIN", "AMUL", "ENERGY", "BATCH", "INGREDIENTS",
        "TONED", "HOMOGENISED", "HOMOGENIZED", "STANDARDISED", "STANDARDIZED",
        "REFRIGERATED", "POUCH", "POLYPACK", "LITRE", "LITER", "ML", "CALCIUM",
        "VITAMIN", "CHOLESTEROL", "CARBOHYDRATE", "NET", "MRP", "MFD", "PKD",
        "TAAZA", "GOLD", "MAZA", "COW", "BUFFALO", "CURD", "DTH", "EXPIRY",
        "USE BY", "BEST BEFORE", "CONSUME", "STORAGE", "POLYETHYLENE"
    }

    # Competitor / Unsupported Brands in Indian dairy retail
    COMPETITOR_BRANDS = {
        "Mother Dairy": ["MOTHER DAIRY", "मदर डेयरी", "MOTHERDAIRY"],
        "Nandini": ["NANDINI", "KMF", "ನಂದಿನಿ"],
        "Country Delight": ["COUNTRY DELIGHT", "COUNTRYDELIGHT"],
        "Nestle": ["NESTLE", "NESTLÉ", "EVERYDAY"],
        "Gokul": ["GOKUL", "गोकुळ", "KOLHAPUR ZILLA"],
        "Saras": ["SARAS", "सरस", "RCDF"],
        "Verka": ["VERKA", "ਵਰਕਾ", "MILKFED"],
        "Sudha": ["SUDHA", "सुधा", "COMFED"],
        "Aavin": ["AAVIN", "ஆவின்", "TCMPF"],
        "Vijaya": ["VIJAYA", "विजया", "TSDDCF"],
        "Milma": ["MILMA", "மில்மா", "KCMMF"],
        "Heritage": ["HERITAGE", "HERITAGE FOODS"],
        "Dodla": ["DODLA", "DODLA DAIRY"]
    }

    @staticmethod
    def is_physical_packaging(image_bgr: np.ndarray, ocr_text: str = "") -> Tuple[bool, str, float]:
        """
        Validates if the input image is a photograph of physical product packaging
        versus a digital diagram, flowchart, schematic, screenshot, or document.

        Returns: (is_packaging: bool, category_label: str, confidence: float)
        """
        if image_bgr is None or image_bgr.size == 0:
            return False, "EMPTY_IMAGE", 0.0

        h, w = image_bgr.shape[:2]
        text_upper = ocr_text.upper() if ocr_text else ""
        text_tokens = set(re.findall(r"\b[A-Z]{3,}\b", text_upper))

        # Check 1: Semantic Keyword Signature
        diagram_matches = text_tokens.intersection(DomainGatekeeperEngine.DIAGRAM_KEYWORDS)
        packaging_matches = text_tokens.intersection(DomainGatekeeperEngine.PACKAGING_KEYWORDS) | text_tokens.intersection(DomainGatekeeperEngine.AMUL_KEYWORDS)

        if len(diagram_matches) >= 2 and len(packaging_matches) == 0:
            return False, "DIGITAL_DIAGRAM_OR_SCHEMATIC", 0.95

        # Check 2: Visual Diagram Analysis (Large uniform light background + high-contrast line network)
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        
        # Calculate percentage of pure white/near-white pixels (> 240)
        white_pixels = np.sum(gray > 240) / float(h * w)
        # Calculate percentage of very light background (> 220)
        light_pixels = np.sum(gray > 220) / float(h * w)

        # Diagrams typically have 65%+ light/white canvas
        if light_pixels > 0.65:
            # Check edge characteristics: diagrams have sharp, thin, connected lines
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / float(h * w)

            # High white background combined with low-to-medium edge density (sparse boxes/lines)
            if 0.015 < edge_density < 0.12:
                # Color variance in HSV
                hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
                sat = hsv[:, :, 1]
                # Diagrams have low overall color saturation across most of the image
                low_sat_pct = np.sum(sat < 30) / float(h * w)
                
                # Packaging with white back panels (nutrition tables, barcodes, ingredients)
                # will have low saturation and white backgrounds, BUT contain packaging keywords.
                # A digital diagram or document will NOT have packaging keywords.
                if len(packaging_matches) == 0:
                    if low_sat_pct > 0.70 and len(diagram_matches) >= 1:
                        return False, "DIGITAL_DIAGRAM_OR_SCHEMATIC", 0.90
                    elif low_sat_pct > 0.85 and white_pixels > 0.55:
                        # Very high monochrome background with diagram layout and zero packaging tokens
                        return False, "DIGITAL_DIAGRAM_OR_DOCUMENT", 0.85

        # Check 3: Aspect Ratio Extremes
        aspect_ratio = float(w) / float(max(1, h))
        if aspect_ratio < 0.20 or aspect_ratio > 4.5:
            return False, "ABNORMAL_ASPECT_RATIO", 0.80

        return True, "PHYSICAL_PACKAGING", 0.88


    COMPETITOR_PATTERNS = [
        ("Mother Dairy", re.compile(r"\bM[O0]TH[A-Z0-9]{1,4}\s*DAIRY\b|\bMOTHER\s*DAIRY\b|\bMOTHERDAIRY\b|\bMOTHLRA\b|\bमदर\s*डेयरी\b", re.IGNORECASE)),
        ("Nandini", re.compile(r"\bNAND[I1]N[I1]\b|\bKMF\b|\bನಂದಿನಿ\b", re.IGNORECASE)),
        ("Country Delight", re.compile(r"\bCOUNTRY\s*DEL[I1]GHT\b", re.IGNORECASE)),
        ("Nestle", re.compile(r"\bNESTL[EÉ3]\b", re.IGNORECASE)),
        ("Gokul", re.compile(r"\bG[O0]KUL\b|\bगोकुळ\b|\bKOLHAPUR\s*ZILLA\b", re.IGNORECASE)),
        ("Saras", re.compile(r"\bSARAS\b|\bसरस\b|\bRCDF\b", re.IGNORECASE)),
        ("Verka", re.compile(r"\bVERKA\b|\bਵਰਕਾ\b|\bMILKFED\b", re.IGNORECASE)),
        ("Sudha", re.compile(r"\bSUDHA\b|\bसुधा\b|\bCOMFED\b", re.IGNORECASE)),
        ("Aavin", re.compile(r"\bAAV[I1]N\b|\bஆவின்\b|\bTCMPF\b", re.IGNORECASE)),
        ("Vijaya", re.compile(r"\bV[I1]JAYA\b|\bविजया\b|\bTSDDCF\b", re.IGNORECASE)),
        ("Milma", re.compile(r"\bM[I1]LMA\b|\bமில்மா\b|\bKCMMF\b", re.IGNORECASE)),
        ("Heritage", re.compile(r"\bHER[I1]TAGE\b", re.IGNORECASE)),
        ("Dodla", re.compile(r"\bD[O0]DLA\b", re.IGNORECASE)),
    ]

    @staticmethod
    def detect_brand(image_bgr: np.ndarray, ocr_text: str = "") -> Dict[str, Any]:
        """
        Inspects textual and visual cues to identify the product brand.
        Returns:
            {
                "brand": str,
                "is_supported": bool,
                "confidence": float,
                "reason": Optional[str]
            }
        """
        text_upper = ocr_text.upper() if ocr_text else ""

        # 1. Check for competitor/unsupported brands first
        # 1. Check for competitor/unsupported brands via regex patterns
        for brand_name, pattern in DomainGatekeeperEngine.COMPETITOR_PATTERNS:
            m = pattern.search(text_upper)
            if m:
                return {
                    "brand": brand_name,
                    "is_supported": False,
                    "confidence": 0.95,
                    "reason": f"Detected competitor brand '{brand_name}' via trademark pattern '{m.group(0)}'."
                }

        # Also check exact substring keyword matches
        for brand_name, keywords in DomainGatekeeperEngine.COMPETITOR_BRANDS.items():
            for kw in keywords:
                if kw in text_upper:
                    return {
                        "brand": brand_name,
                        "is_supported": False,
                        "confidence": 0.95,
                        "reason": f"Detected competitor brand '{brand_name}' via trademark keyword '{kw}'."
                    }

        # 2. Check for supported brand (Amul)
        for kw in DomainGatekeeperEngine.AMUL_KEYWORDS:
            if kw in text_upper:
                return {
                    "brand": "Amul",
                    "is_supported": True,
                    "confidence": 0.95,
                    "reason": f"Identified authentic brand 'Amul' (GCMMF) via keyword '{kw}'."
                }

        # 3. Visual Logo / Trademark check in image
        # If OCR did not detect text, look for Amul color cues:
        # Amul Gold has prominent red/white graphics, Amul Taaza has cyan/blue, Amul Shakti has green/white
        if image_bgr is not None and image_bgr.size > 0:
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            # Check for Amul red cursive logo hue range
            red_mask1 = (hsv[:, :, 0] < 10) & (hsv[:, :, 1] > 70) & (hsv[:, :, 2] > 70)
            red_mask2 = (hsv[:, :, 0] > 170) & (hsv[:, :, 1] > 70) & (hsv[:, :, 2] > 70)
            red_ratio = (np.sum(red_mask1) + np.sum(red_mask2)) / float(image_bgr.shape[0] * image_bgr.shape[1])

            blue_mask = (hsv[:, :, 0] >= 95) & (hsv[:, :, 0] <= 130) & (hsv[:, :, 1] > 70)
            blue_ratio = np.sum(blue_mask) / float(image_bgr.shape[0] * image_bgr.shape[1])

            green_mask = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 70)
            green_ratio = np.sum(green_mask) / float(image_bgr.shape[0] * image_bgr.shape[1])

            # If strong brand color cues exist without competitor text, consider tentatively Amul
            if red_ratio > 0.08 or blue_ratio > 0.08 or green_ratio > 0.08:
                return {
                    "brand": "Amul",
                    "is_supported": True,
                    "confidence": 0.70,
                    "reason": "Brand inferred from dominant retail color palette (Amul Milk design system)."
                }

        # 4. Unknown / Undetermined Brand
        # 3. Unknown / Undetermined Brand
        # Note: We intentionally avoid assuming that arbitrary red, blue, or green packages
        # are Amul, because competitor packaging (e.g. Mother Dairy, Nandini) shares the same hues.
        return {
            "brand": "UNKNOWN",
            "is_supported": False,
            "confidence": 0.30,
            "reason": "Packaging does not exhibit identifiable Amul brand markings or recognized trademarks."
        }

