import os
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.ai.certification.engine import CertificationAnalyzer
from backend.app.ai.codes.barcode import BarcodeAnalyzer
from backend.app.ai.codes.qr import QRAnalyzer
from backend.app.ai.contracts import DecisionResult, DecisionState, EvidenceObject, QualityAssessmentResult
from backend.app.ai.decision.engine import DecisionEngine
from backend.app.ai.detection.engine import ProductDetector
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
    Quality -> Detection -> Retrieval -> Evidence Engines -> Heatmap -> Fusion -> Decision -> Fingerprint -> Report.
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

    async def execute_pipeline(
        self,
        db: AsyncSession,
        scan_id: str,
        image_bgr: np.ndarray,
        view_type: str = "FRONT"
    ) -> Dict[str, Any]:
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

        # Stage 3: OCR & Barcode extraction for Candidate Retrieval
        raw_text, ocr_conf, _ = self.ocr_engine.extract_text(crop_bgr)
        barcode_ev = self.barcode_analyzer.analyze(crop_bgr)
        detected_barcode = barcode_ev.features.get("decoded_value") if barcode_ev.availability else None

        # Stage 4: Hierarchical Reference Retrieval
        candidates = await ReferenceRetriever.retrieve_candidates(
            db=db,
            detected_text=raw_text,
            detected_barcode=detected_barcode,
            view_type=view_type,
            crop_bgr=crop_bgr
        )
        best_candidate = candidates[0] if candidates else None

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
        evidences: List[EvidenceObject] = []

        # Vision Engines
        evidences.append(self.logo_analyzer.analyze(crop_bgr, ref_crop_bgr, ref_meta))
        evidences.append(self.layout_analyzer.analyze(crop_bgr, ref_crop_bgr, ref_meta))
        evidences.append(self.colour_analyzer.analyze(crop_bgr, ref_crop_bgr, ref_meta))
        evidences.append(self.typography_analyzer.analyze(crop_bgr, ref_crop_bgr, ref_meta))
        evidences.append(self.texture_analyzer.analyze(crop_bgr, ref_crop_bgr, ref_meta))
        evidences.append(self.shape_analyzer.analyze(crop_bgr, ref_crop_bgr, ref_meta))
        evidences.append(self.seal_analyzer.analyze(crop_bgr, ref_crop_bgr, ref_meta))
        evidences.append(self.print_analyzer.analyze(crop_bgr, ref_crop_bgr, ref_meta))

        # Text & Codes
        evidences.append(self.ocr_engine.analyze(crop_bgr, ref_meta))
        evidences.append(barcode_ev)
        evidences.append(self.qr_analyzer.analyze(crop_bgr, ref_meta))
        evidences.append(self.cert_analyzer.analyze(raw_text, ref_meta))

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


orchestrator = AIOrchestrator()
