from typing import Any

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ai.certification.engine import CertificationAnalyzer
from backend.app.ai.codes.barcode import BarcodeAnalyzer
from backend.app.ai.codes.qr import QRAnalyzer
from backend.app.ai.contracts import EvidenceObject, EvidenceType, QualityAssessmentResult
from backend.app.ai.decision.engine import DecisionEngine
from backend.app.ai.detection.engine import ProductDetector
from backend.app.ai.domain.gatekeeper import DomainGatekeeperEngine
from backend.app.ai.explainability.engine import DifferenceHeatmapEngine, ExplanationEngine
from backend.app.ai.fingerprint.engine import PackagingFingerprintEngine
from backend.app.ai.fusion.engine import MultiEvidenceFusionEngine
from backend.app.ai.ocr.engine import OCREngine
from backend.app.ai.quality.engine import ImageQualityEngine
from backend.app.ai.reporting.pdf_generator import VeriSurePDFGenerator
from backend.app.ai.retrieval.engine import ReferenceRetriever
from backend.app.ai.vision.colour import ColourAnalyzer
from backend.app.ai.vision.layout import LayoutAnalyzer
from backend.app.ai.vision.logo import LogoAnalyzer
from backend.app.ai.vision.print import PrintQualityAnalyzer
from backend.app.ai.vision.seal import SealAnalyzer
from backend.app.ai.vision.shape import ShapeAnalyzer
from backend.app.ai.vision.texture import TextureAnalyzer
from backend.app.ai.vision.typography import TypographyAnalyzer
from backend.app.core.storage import storage


class AIOrchestrator:
    """
    Coordinates the multi-stage, multi-engine verification pipeline:
    Quality -> Detection -> Domain Validation -> Retrieval -> Evidence Engines -> Heatmap -> Fusion -> Decision -> Fingerprint -> Report.
    Supports both Single-Panel and Dual-Panel (Front + Back) 360° Assessment.
    """
    def __init__(self):
        self.quality_engine = ImageQualityEngine()
        self.detector = ProductDetector()
        self.ocr_engine = OCREngine()
        self.barcode_analyzer = BarcodeAnalyzer()
        self.qr_analyzer = QRAnalyzer()
        self.cert_analyzer = CertificationAnalyzer()
        self.logo_analyzer = LogoAnalyzer()
        self.layout_analyzer = LayoutAnalyzer()
        self.colour_analyzer = ColourAnalyzer()
        self.typography_analyzer = TypographyAnalyzer()
        self.texture_analyzer = TextureAnalyzer()
        self.shape_analyzer = ShapeAnalyzer()
        self.seal_analyzer = SealAnalyzer()
        self.print_analyzer = PrintQualityAnalyzer()
        self.fusion_engine = MultiEvidenceFusionEngine()
        self.decision_engine = DecisionEngine()

    @staticmethod
    def _safe_analyze(analyzer_fn, *args, ev_type: EvidenceType, source: str, **kwargs) -> EvidenceObject:
        """
        Fault-isolation barrier: ensures any engine crash or exception returns a standardized
        non-available EvidenceObject rather than crashing the pipeline or fabricating evidence.
        """
        try:
            res = analyzer_fn(*args, **kwargs)
            if isinstance(res, EvidenceObject):
                return res
            return EvidenceObject(
                type=ev_type,
                score=None,
                confidence=0.10,
                quality=0.10,
                availability=False,
                source=source,
                explanation=f"Analyzer returned non-EvidenceObject: {type(res)}",
                features={}
            )
        except Exception as exc:
            import logging
            logging.getLogger("verisure.ai").warning(f"Engine {source} ({ev_type.value}) exception: {exc}")
            return EvidenceObject(
                type=ev_type,
                score=None,
                confidence=0.10,
                quality=0.10,
                availability=False,
                source=source,
                explanation=f"Evidence extraction unavailable due to engine exception: {str(exc)[:100]}",
                features={"error": str(exc)}
            )

    async def execute_pipeline(
        self,
        db: AsyncSession,
        scan_id: str,
        image_bgr: np.ndarray,
        view_type: str = "FRONT"
    ) -> dict[str, Any]:
        # Stage 1: Image Quality Assessment
        quality_result = self.quality_engine.assess(image_bgr)

        # Stage 2: Product Detection & Cropping
        det_box, crop_bgr = self.detector.detect(image_bgr)

        # Save crop image
        _, crop_png = cv2.imencode(".png", crop_bgr)
        crop_rel_path, crop_abs_path = await storage.save_bytes(
            data=crop_png.tobytes(),
            subfolder="crops",
            filename=f"crop_{scan_id}_{view_type.lower()}",
            extension=".png"
        )

        if not quality_result.usable:
            decision = self.decision_engine.evaluate(
                fusion_result={
                    "fused_authenticity_score": 0.50,
                    "risk_score": 50.0,
                    "confidence": 0.30,
                    "uncertainty": 0.90,
                    "evidence_coverage": 0.0,
                    "conflicts": []
                },
                quality_result=quality_result,
                evidences=[]
            )
            return {
                "quality": quality_result,
                "detection": det_box,
                "crop_path": crop_rel_path,
                "heatmap_path": None,
                "evidences": [],
                "decision": decision,
                "fingerprint": None,
                "report_path": None,
                "identified_product": None
            }

        # Stage 3: OCR & Barcode extraction
        raw_text, ocr_conf, _ = self.ocr_engine.extract_text(crop_bgr)
        barcode_ev = self.barcode_analyzer.analyze(crop_bgr)
        detected_barcode = barcode_ev.features.get("decoded_value") if barcode_ev.availability else None

        # Stage 3.5: Domain Gatekeeper & Brand Validation
        is_pkg, pkg_cat, _ = DomainGatekeeperEngine.is_physical_packaging(crop_bgr, raw_text)
        brand_info = DomainGatekeeperEngine.detect_brand(crop_bgr, raw_text)

        # Rejection Gate A: Digital Diagrams, Schematics, or Documents
        if not is_pkg:
            decision = self.decision_engine.evaluate(
                fusion_result={
                    "fused_authenticity_score": 0.0,
                    "risk_score": 0.0,
                    "confidence": 0.10,
                    "uncertainty": 0.95,
                    "evidence_coverage": 0.0,
                    "conflicts": []
                },
                quality_result=quality_result,
                evidences=[],
                is_packaging=False,
                packaging_category=pkg_cat
            )
            return {
                "quality": quality_result,
                "detection": det_box,
                "crop_path": crop_rel_path,
                "heatmap_path": None,
                "evidences": [],
                "decision": decision,
                "fingerprint": None,
                "report_path": None,
                "identified_product": None
            }

        # Rejection Gate B: Competitor / Unsupported Brands (e.g. Mother Dairy, Nandini, Nestle)
        if not brand_info["is_supported"] and brand_info["brand"] != "UNKNOWN":
            decision = self.decision_engine.evaluate(
                fusion_result={
                    "fused_authenticity_score": 0.0,
                    "risk_score": 0.0,
                    "confidence": 0.90,
                    "uncertainty": 0.10,
                    "evidence_coverage": 0.0,
                    "conflicts": []
                },
                quality_result=quality_result,
                evidences=[],
                is_packaging=True,
                is_supported_brand=False,
                detected_brand=brand_info["brand"],
                brand_reason=brand_info["reason"]
            )
            return {
                "quality": quality_result,
                "detection": det_box,
                "crop_path": crop_rel_path,
                "heatmap_path": None,
                "evidences": [],
                "decision": decision,
                "fingerprint": None,
                "report_path": None,
                "identified_product": None
            }

        # Stage 4: Hierarchical Reference Retrieval
        candidates = await ReferenceRetriever.retrieve_candidates(
            db=db,
            detected_text=raw_text,
            detected_barcode=detected_barcode,
            view_type=view_type,
            crop_bgr=crop_bgr
        )
        best_candidate = candidates[0] if candidates else None

        # Rejection Gate C: Product Not Identified / Unrecognized Packaging
        if best_candidate is None:
            decision = self.decision_engine.evaluate(
                fusion_result={
                    "fused_authenticity_score": 0.0,
                    "risk_score": 0.0,
                    "confidence": 0.30,
                    "uncertainty": 0.85,
                    "evidence_coverage": 0.0,
                    "conflicts": []
                },
                quality_result=quality_result,
                evidences=[],
                product_identified=False
            )
            return {
                "quality": quality_result,
                "detection": det_box,
                "crop_path": crop_rel_path,
                "heatmap_path": None,
                "evidences": [],
                "decision": decision,
                "fingerprint": None,
                "report_path": None,
                "identified_product": None
            }

        # Load reference crop if available
        ref_crop_bgr = None
        ref_meta = {}
        if best_candidate and best_candidate.get("reference_image_path"):
            ref_path = storage.get_absolute_path(best_candidate["reference_image_path"])
            if ref_path.exists():
                ref_crop_bgr = cv2.imread(str(ref_path))
            ref_meta = {
                "expected_barcode": best_candidate.get("expected_barcode"),
                "expected_fssai": best_candidate.get("expected_fssai"),
                "expected_mrp": best_candidate.get("expected_mrp")
            }

        # Stage 5: Independent Evidence Analysis Engines
        evidences: list[EvidenceObject] = [
            # Vision Engines
            self._safe_analyze(self.logo_analyzer.analyze, crop_bgr, ref_crop_bgr, ref_meta, ev_type=EvidenceType.LOGO, source="verisure-logo-orb-v1"),
            self._safe_analyze(self.layout_analyzer.analyze, crop_bgr, ref_crop_bgr, ref_meta, ev_type=EvidenceType.LAYOUT, source="verisure-layout-sift-v1"),
            self._safe_analyze(self.colour_analyzer.analyze, crop_bgr, ref_crop_bgr, ref_meta, ev_type=EvidenceType.COLOUR, source="verisure-colour-hist-v1"),
            self._safe_analyze(self.typography_analyzer.analyze, crop_bgr, ref_crop_bgr, ref_meta, ev_type=EvidenceType.TYPOGRAPHY, source="verisure-typo-contour-v1"),
            self._safe_analyze(self.texture_analyzer.analyze, crop_bgr, ref_crop_bgr, ref_meta, ev_type=EvidenceType.TEXTURE, source="verisure-texture-glcm-v1"),
            self._safe_analyze(self.shape_analyzer.analyze, crop_bgr, ref_crop_bgr, ref_meta, ev_type=EvidenceType.SHAPE, source="verisure-shape-hu-v1"),
            self._safe_analyze(self.seal_analyzer.analyze, crop_bgr, ref_crop_bgr, ref_meta, ev_type=EvidenceType.SEAL, source="verisure-seal-sobel-v1"),
            self._safe_analyze(self.print_analyzer.analyze, crop_bgr, ref_crop_bgr, ref_meta, ev_type=EvidenceType.PRINT, source="verisure-print-laplacian-v1"),

            # Text & Codes
            self._safe_analyze(self.ocr_engine.analyze, crop_bgr, ref_meta, ev_type=EvidenceType.OCR, source="verisure-ocr-engine-v1"),
            barcode_ev if isinstance(barcode_ev, EvidenceObject) else self._safe_analyze(lambda: barcode_ev, ev_type=EvidenceType.BARCODE, source="verisure-barcode-pyzbar-v1"),
            self._safe_analyze(self.qr_analyzer.analyze, crop_bgr, ref_meta, ev_type=EvidenceType.QR, source="verisure-qr-wechat-v1"),
            self._safe_analyze(self.cert_analyzer.analyze, raw_text, ref_meta, ev_type=EvidenceType.CERTIFICATION, source="verisure-cert-regex-v1"),
        ]

        # Stage 6: Difference Heatmap & Suspicious Regions
        heatmap_bgr, anomaly_regions = DifferenceHeatmapEngine.generate_heatmap(crop_bgr, ref_crop_bgr)
        _, heatmap_png = cv2.imencode(".png", heatmap_bgr)
        heatmap_rel_path, heatmap_abs_path = await storage.save_bytes(
            data=heatmap_png.tobytes(),
            subfolder="heatmaps",
            filename=f"heatmap_{scan_id}_{view_type.lower()}",
            extension=".png"
        )

        # Stage 7: Multi-Evidence Fusion
        fusion_result = self.fusion_engine.fuse(evidences, quality_result)

        # Stage 8: Decision Engine
        decision = self.decision_engine.evaluate(
            fusion_result=fusion_result,
            quality_result=quality_result,
            evidences=evidences,
            product_identified=best_candidate is not None
        )

        # Stage 9: Grounded Narrative Explanation
        prod_title = best_candidate["product_name"] if best_candidate else "Unknown Dairy Product"
        pkg_ver = best_candidate["version_code"] if best_candidate else "Unknown"
        decision.explanation_summary = ExplanationEngine.generate_narrative(
            decision=decision,
            evidences=evidences,
            product_name=prod_title,
            packaging_version=pkg_ver
        )
        decision.suspicious_regions = anomaly_regions

        # Stage 10: Packaging Fingerprint Generation
        fingerprint = PackagingFingerprintEngine.generate_fingerprint(
            product_metadata={
                "brand": "AMUL",
                "product": prod_title,
                "variant": best_candidate["variant_name"] if best_candidate else "Standard",
                "pack_size": best_candidate["pack_size"] if best_candidate else "Unknown",
                "packaging_version": pkg_ver
            },
            evidences=evidences,
            regions=[r.model_dump() for r in anomaly_regions]
        )

        # Stage 11: PDF Report Generation
        report_filename = f"report_{scan_id}.pdf"
        report_abs_path = storage.get_absolute_path(f"reports/{report_filename}")
        VeriSurePDFGenerator.generate_report(
            output_pdf_path=str(report_abs_path),
            scan_id=scan_id,
            product_metadata={
                "brand": "AMUL",
                "product": prod_title,
                "variant": best_candidate["variant_name"] if best_candidate else "Standard",
                "pack_size": best_candidate["pack_size"] if best_candidate else "Unknown",
                "packaging_version": pkg_ver
            },
            decision=decision,
            evidences=evidences,
            quality_details=quality_result.model_dump()
        )

        return {
            "quality": quality_result,
            "detection": det_box,
            "crop_path": crop_rel_path,
            "heatmap_path": heatmap_rel_path,
            "evidences": evidences,
            "decision": decision,
            "fingerprint": fingerprint,
            "report_path": f"reports/{report_filename}",
            "identified_product": best_candidate
        }

    async def execute_dual_pipeline(
        self,
        db: AsyncSession,
        scan_id: str,
        image_front_bgr: np.ndarray,
        image_back_bgr: np.ndarray
    ) -> dict[str, Any]:
        """
        Executes comprehensive 360° dual-side product verification across both Front and Back panels:
        1. Front Side: Evaluates Brand Logo, Typography, Layout, Colour, Shape, Texture, Front Seals.
        2. Back Side: Evaluates Barcode (EAN-13), QR Code, FSSAI License, Print Quality, Back Seals, Nutrition OCR.
        3. Cross-Side Consistency Check: Validates that Front identified product variant matches Back barcode.
        """
        # --- FRONT PANEL ANALYSIS ---
        qual_front = self.quality_engine.assess(image_front_bgr)
        det_front, crop_front_bgr = self.detector.detect(image_front_bgr)
        _, crop_front_png = cv2.imencode(".png", crop_front_bgr)
        crop_front_rel, _ = await storage.save_bytes(
            data=crop_front_png.tobytes(),
            subfolder="crops",
            filename=f"crop_{scan_id}_front",
            extension=".png"
        )

        raw_text_front, _, _ = self.ocr_engine.extract_text(crop_front_bgr)

        # Domain & Brand Check on Front
        is_pkg_front, pkg_cat_front, _ = DomainGatekeeperEngine.is_physical_packaging(crop_front_bgr, raw_text_front)
        brand_front = DomainGatekeeperEngine.detect_brand(crop_front_bgr, raw_text_front)

        if not is_pkg_front:
            dec = self.decision_engine.evaluate(
                fusion_result={"fused_authenticity_score": 0.0, "risk_score": 0.0, "confidence": 0.1, "uncertainty": 0.95, "evidence_coverage": 0.0, "conflicts": []},
                quality_result=qual_front, evidences=[], is_packaging=False, packaging_category=pkg_cat_front
            )
            return {"images": [{"view_type": "FRONT", "quality": qual_front, "detection": det_front, "crop_path": crop_front_rel, "heatmap_path": None}], "decision": dec, "evidences": [], "report_path": None, "identified_product": None}

        if not brand_front["is_supported"] and brand_front["brand"] != "UNKNOWN":
            dec = self.decision_engine.evaluate(
                fusion_result={"fused_authenticity_score": 0.0, "risk_score": 0.0, "confidence": 0.9, "uncertainty": 0.1, "evidence_coverage": 0.0, "conflicts": []},
                quality_result=qual_front, evidences=[], is_packaging=True, is_supported_brand=False, detected_brand=brand_front["brand"], brand_reason=brand_front["reason"]
            )
            return {"images": [{"view_type": "FRONT", "quality": qual_front, "detection": det_front, "crop_path": crop_front_rel, "heatmap_path": None}], "decision": dec, "evidences": [], "report_path": None, "identified_product": None}

        # --- BACK PANEL ANALYSIS ---
        qual_back = self.quality_engine.assess(image_back_bgr)
        det_back, crop_back_bgr = self.detector.detect(image_back_bgr)
        _, crop_back_png = cv2.imencode(".png", crop_back_bgr)
        crop_back_rel, _ = await storage.save_bytes(
            data=crop_back_png.tobytes(),
            subfolder="crops",
            filename=f"crop_{scan_id}_back",
            extension=".png"
        )

        raw_text_back, _, _ = self.ocr_engine.extract_text(crop_back_bgr)
        barcode_ev = self.barcode_analyzer.analyze(crop_back_bgr)
        detected_barcode = barcode_ev.features.get("decoded_value") if barcode_ev.availability else None

        # Domain & Brand Check on Back
        is_pkg_back, pkg_cat_back, _ = DomainGatekeeperEngine.is_physical_packaging(crop_back_bgr, raw_text_back)
        brand_back = DomainGatekeeperEngine.detect_brand(crop_back_bgr, raw_text_back)

        if not is_pkg_back:
            dec = self.decision_engine.evaluate(
                fusion_result={"fused_authenticity_score": 0.0, "risk_score": 0.0, "confidence": 0.1, "uncertainty": 0.95, "evidence_coverage": 0.0, "conflicts": []},
                quality_result=qual_back, evidences=[], is_packaging=False, packaging_category=pkg_cat_back
            )
            return {"images": [{"view_type": "FRONT", "quality": qual_front, "detection": det_front, "crop_path": crop_front_rel, "heatmap_path": None}, {"view_type": "BACK", "quality": qual_back, "detection": det_back, "crop_path": crop_back_rel, "heatmap_path": None}], "decision": dec, "evidences": [], "report_path": None, "identified_product": None}

        if not brand_back["is_supported"] and brand_back["brand"] != "UNKNOWN":
            dec = self.decision_engine.evaluate(
                fusion_result={"fused_authenticity_score": 0.0, "risk_score": 0.0, "confidence": 0.9, "uncertainty": 0.1, "evidence_coverage": 0.0, "conflicts": []},
                quality_result=qual_back, evidences=[], is_packaging=True, is_supported_brand=False, detected_brand=brand_back["brand"], brand_reason=brand_back["reason"]
            )
            return {"images": [{"view_type": "FRONT", "quality": qual_front, "detection": det_front, "crop_path": crop_front_rel, "heatmap_path": None}, {"view_type": "BACK", "quality": qual_back, "detection": det_back, "crop_path": crop_back_rel, "heatmap_path": None}], "decision": dec, "evidences": [], "report_path": None, "identified_product": None}

        # Check for duplicate / identical views (Case D: Two front images or identical pair submitted)
        is_duplicate = False
        try:
            gray1 = cv2.cvtColor(cv2.resize(crop_front_bgr, (256, 256)), cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(cv2.resize(crop_back_bgr, (256, 256)), cv2.COLOR_BGR2GRAY)
            mse = float(np.mean((gray1.astype(np.float32) - gray2.astype(np.float32)) ** 2))
            if mse < 50.0:
                is_duplicate = True
        except Exception:
            pass

        if is_duplicate:
            dec = self.decision_engine.evaluate(
                fusion_result={"fused_authenticity_score": 0.50, "risk_score": 50.0, "confidence": 0.30, "uncertainty": 0.85, "evidence_coverage": 0.0, "conflicts": []},
                quality_result=qual_front,
                evidences=[],
                duplicate_views=True
            )
            return {
                "images": [
                    {"view_type": "FRONT", "quality": qual_front, "detection": det_front, "crop_path": crop_front_rel, "heatmap_path": None},
                    {"view_type": "BACK", "quality": qual_back, "detection": det_back, "crop_path": crop_back_rel, "heatmap_path": None}
                ],
                "decision": dec,
                "evidences": [],
                "report_path": None,
                "identified_product": None
            }

        # --- CANDIDATE RETRIEVAL (Fused Front + Back text and Barcode) ---
        fused_text = f"{raw_text_front} {raw_text_back}"
        candidates = await ReferenceRetriever.retrieve_candidates(
            db=db,
            detected_text=fused_text,
            detected_barcode=detected_barcode,
            view_type="FRONT",
            crop_bgr=crop_front_bgr
        )
        best_candidate = candidates[0] if candidates else None

        if best_candidate is None:
            dec = self.decision_engine.evaluate(
                fusion_result={"fused_authenticity_score": 0.0, "risk_score": 0.0, "confidence": 0.3, "uncertainty": 0.85, "evidence_coverage": 0.0, "conflicts": []},
                quality_result=qual_front, evidences=[], product_identified=False
            )
            return {"images": [{"view_type": "FRONT", "quality": qual_front, "detection": det_front, "crop_path": crop_front_rel, "heatmap_path": None}, {"view_type": "BACK", "quality": qual_back, "detection": det_back, "crop_path": crop_back_rel, "heatmap_path": None}], "decision": dec, "evidences": [], "report_path": None, "identified_product": None}

        # Retrieve Reference Crops for Front and Back
        ref_front_bgr = None
        ref_back_bgr = None
        ref_meta = {
            "expected_barcode": best_candidate.get("expected_barcode"),
            "expected_fssai": best_candidate.get("expected_fssai"),
            "expected_mrp": best_candidate.get("expected_mrp")
        }

        # Fetch front and back references from database
        from backend.app.models.reference import ReferenceImage
        refs = (await db.execute(
            select(ReferenceImage)
            .where((ReferenceImage.packaging_version_id == best_candidate["packaging_version_id"]) & (ReferenceImage.approval_status == "APPROVED"))
        )).scalars().all()

        for r in refs:
            p = storage.get_absolute_path(r.image_path)
            if p.exists():
                if r.view_type == "FRONT" and ref_front_bgr is None:
                    ref_front_bgr = cv2.imread(str(p))
                elif r.view_type == "BACK" and ref_back_bgr is None:
                    ref_back_bgr = cv2.imread(str(p))

        # --- DUAL-SIDE EVIDENCE ENGINES ---
        evidences: list[EvidenceObject] = [
            # Front Vision Models
            self._safe_analyze(self.logo_analyzer.analyze, crop_front_bgr, ref_front_bgr, ref_meta, ev_type=EvidenceType.LOGO, source="verisure-logo-orb-v1"),
            self._safe_analyze(self.layout_analyzer.analyze, crop_front_bgr, ref_front_bgr, ref_meta, ev_type=EvidenceType.LAYOUT, source="verisure-layout-sift-v1"),
            self._safe_analyze(self.colour_analyzer.analyze, crop_front_bgr, ref_front_bgr, ref_meta, ev_type=EvidenceType.COLOUR, source="verisure-colour-hist-v1"),
            self._safe_analyze(self.typography_analyzer.analyze, crop_front_bgr, ref_front_bgr, ref_meta, ev_type=EvidenceType.TYPOGRAPHY, source="verisure-typo-contour-v1"),
            self._safe_analyze(self.shape_analyzer.analyze, crop_front_bgr, ref_front_bgr, ref_meta, ev_type=EvidenceType.SHAPE, source="verisure-shape-hu-v1"),
            self._safe_analyze(self.texture_analyzer.analyze, crop_front_bgr, ref_front_bgr, ref_meta, ev_type=EvidenceType.TEXTURE, source="verisure-texture-glcm-v1"),
            self._safe_analyze(self.seal_analyzer.analyze, crop_front_bgr, ref_front_bgr, ref_meta, ev_type=EvidenceType.SEAL, source="verisure-seal-sobel-v1"),

            # Back Compliance Models
            barcode_ev if isinstance(barcode_ev, EvidenceObject) else self._safe_analyze(lambda: barcode_ev, ev_type=EvidenceType.BARCODE, source="verisure-barcode-pyzbar-v1"),
            self._safe_analyze(self.qr_analyzer.analyze, crop_back_bgr, ref_meta, ev_type=EvidenceType.QR, source="verisure-qr-wechat-v1"),
            self._safe_analyze(self.cert_analyzer.analyze, raw_text_back, ref_meta, ev_type=EvidenceType.CERTIFICATION, source="verisure-cert-regex-v1"),
            self._safe_analyze(self.print_analyzer.analyze, crop_back_bgr, ref_back_bgr, ref_meta, ev_type=EvidenceType.PRINT, source="verisure-print-laplacian-v1"),
            self._safe_analyze(self.ocr_engine.analyze, crop_back_bgr, ref_meta, ev_type=EvidenceType.OCR, source="verisure-ocr-engine-v1"),
        ]

        # --- HEATMAPS FOR BOTH SIDES ---
        heat_front_bgr, front_anomalies = DifferenceHeatmapEngine.generate_heatmap(crop_front_bgr, ref_front_bgr)
        _, heat_front_png = cv2.imencode(".png", heat_front_bgr)
        heat_front_rel, _ = await storage.save_bytes(data=heat_front_png.tobytes(), subfolder="heatmaps", filename=f"heatmap_{scan_id}_front", extension=".png")

        heat_back_bgr, back_anomalies = DifferenceHeatmapEngine.generate_heatmap(crop_back_bgr, ref_back_bgr)
        _, heat_back_png = cv2.imencode(".png", heat_back_bgr)
        heat_back_rel, _ = await storage.save_bytes(data=heat_back_png.tobytes(), subfolder="heatmaps", filename=f"heatmap_{scan_id}_back", extension=".png")

        # --- CROSS-SIDE CONSISTENCY CHECK ---
        cross_side_conflicts = []
        if detected_barcode and best_candidate.get("expected_barcode") and detected_barcode != best_candidate["expected_barcode"]:
            cross_side_conflicts.append(
                f"Cross-Side Packaging Contradiction: Front graphics identify '{best_candidate['product_name']}', "
                f"but back barcode ('{detected_barcode}') does not match expected barcode ('{best_candidate['expected_barcode']}')."
            )

        # Multi-Evidence Fusion with combined quality
        combined_qual = QualityAssessmentResult(
            overall_quality=round((qual_front.overall_quality + qual_back.overall_quality) / 2.0, 3),
            resolution_score=round((qual_front.resolution_score + qual_back.resolution_score) / 2.0, 3),
            blur_score=round((qual_front.blur_score + qual_back.blur_score) / 2.0, 3),
            brightness_score=round((qual_front.brightness_score + qual_back.brightness_score) / 2.0, 3),
            contrast_score=round((qual_front.contrast_score + qual_back.contrast_score) / 2.0, 3),
            glare_score=round((qual_front.glare_score + qual_back.glare_score) / 2.0, 3),
            occlusion_score=round((qual_front.occlusion_score + qual_back.occlusion_score) / 2.0, 3),
            usable=qual_front.usable and qual_back.usable,
            reasons=list(set(qual_front.reasons + qual_back.reasons)),
            guidance=qual_front.guidance or qual_back.guidance
        )

        fusion_result = self.fusion_engine.fuse(evidences, combined_qual)
        if cross_side_conflicts:
            fusion_result["conflicts"].extend(cross_side_conflicts)
            fusion_result["risk_score"] = min(100.0, fusion_result["risk_score"] + 35.0)

        decision = self.decision_engine.evaluate(
            fusion_result=fusion_result,
            quality_result=combined_qual,
            evidences=evidences,
            product_identified=True
        )

        prod_title = best_candidate["product_name"]
        pkg_ver = best_candidate["version_code"]
        decision.explanation_summary = ExplanationEngine.generate_narrative(
            decision=decision,
            evidences=evidences,
            product_name=prod_title,
            packaging_version=pkg_ver
        )
        if cross_side_conflicts:
            decision.contradictions.extend(cross_side_conflicts)
        decision.suspicious_regions = front_anomalies + back_anomalies

        # Report & Fingerprint
        report_filename = f"report_{scan_id}.pdf"
        report_abs = storage.get_absolute_path(f"reports/{report_filename}")
        VeriSurePDFGenerator.generate_report(
            output_pdf_path=str(report_abs),
            scan_id=scan_id,
            product_metadata={
                "brand": "AMUL",
                "product": prod_title,
                "variant": best_candidate.get("variant_name", "Standard"),
                "pack_size": best_candidate.get("pack_size", "Unknown"),
                "packaging_version": pkg_ver
            },
            decision=decision,
            evidences=evidences,
            quality_details=combined_qual.model_dump()
        )

        fingerprint = PackagingFingerprintEngine.generate_fingerprint(
            product_metadata={
                "brand": "AMUL",
                "product": prod_title,
                "variant": best_candidate.get("variant_name", "Standard"),
                "pack_size": best_candidate.get("pack_size", "Unknown"),
                "packaging_version": pkg_ver
            },
            evidences=evidences,
            regions=[r.model_dump() for r in decision.suspicious_regions]
        )

        return {
            "images": [
                {
                    "view_type": "FRONT",
                    "quality": qual_front,
                    "detection": det_front,
                    "crop_path": crop_front_rel,
                    "heatmap_path": heat_front_rel
                },
                {
                    "view_type": "BACK",
                    "quality": qual_back,
                    "detection": det_back,
                    "crop_path": crop_back_rel,
                    "heatmap_path": heat_back_rel
                }
            ],
            "evidences": evidences,
            "decision": decision,
            "fingerprint": fingerprint,
            "report_path": f"reports/{report_filename}",
            "identified_product": best_candidate
        }


orchestrator = AIOrchestrator()

