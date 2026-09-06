from datetime import datetime
from typing import Any

from backend.app.ai.contracts import EvidenceObject, EvidenceType, PackagingFingerprint


class PackagingFingerprintEngine:
    """
    Constructs a reproducible, serializable, versioned multi-slot packaging fingerprint
    combining visual, textual, machine-readable, and seal characteristics.
    """
    VERSION = "1.0.0"

    @staticmethod
    def generate_fingerprint(
        product_metadata: dict[str, Any],
        evidences: list[EvidenceObject],
        regions: list[dict[str, Any]]
    ) -> PackagingFingerprint:
        ev_map: dict[str, EvidenceObject] = {e.type.value: e for e in evidences}

        # 1. Product Identity slot
        identity_slot = {
            "brand": product_metadata.get("brand", "AMUL"),
            "product": product_metadata.get("product", "Unknown"),
            "variant": product_metadata.get("variant", "Unknown"),
            "pack_size": product_metadata.get("pack_size", "Unknown"),
            "packaging_version": product_metadata.get("packaging_version", "V1")
        }

        # 2. Visual slot
        visual_slot = {
            "logo": ev_map.get(EvidenceType.LOGO.value).features if EvidenceType.LOGO.value in ev_map else {},
            "layout": ev_map.get(EvidenceType.LAYOUT.value).features if EvidenceType.LAYOUT.value in ev_map else {},
            "color": ev_map.get(EvidenceType.COLOUR.value).features if EvidenceType.COLOUR.value in ev_map else {},
            "typography": ev_map.get(EvidenceType.TYPOGRAPHY.value).features if EvidenceType.TYPOGRAPHY.value in ev_map else {},
            "texture": ev_map.get(EvidenceType.TEXTURE.value).features if EvidenceType.TEXTURE.value in ev_map else {},
            "shape": ev_map.get(EvidenceType.SHAPE.value).features if EvidenceType.SHAPE.value in ev_map else {},
            "print": ev_map.get(EvidenceType.PRINT.value).features if EvidenceType.PRINT.value in ev_map else {},
        }

        # 3. Text slot
        ocr_ev = ev_map.get(EvidenceType.OCR.value)
        ocr_features = ocr_ev.features if ocr_ev else {}
        extracted_fields = ocr_features.get("extracted_fields", {})
        text_slot = {
            "ocr_raw_excerpt": ocr_features.get("raw_text", "")[:120],
            "mrp": extracted_fields.get("mrp"),
            "batch": extracted_fields.get("batch"),
            "dates": {
                "mfd": extracted_fields.get("mfd_date"),
                "exp": extracted_fields.get("exp_date")
            },
            "fssai": extracted_fields.get("fssai")
        }

        # 4. Machine Readable slot
        barcode_ev = ev_map.get(EvidenceType.BARCODE.value)
        qr_ev = ev_map.get(EvidenceType.QR.value)
        machine_slot = {
            "barcode": barcode_ev.features if barcode_ev else {},
            "qr": qr_ev.features if qr_ev else {}
        }

        # 5. Packaging integrity slot
        seal_ev = ev_map.get(EvidenceType.SEAL.value)
        packaging_slot = {
            "seal": seal_ev.features if seal_ev else {},
            "tamper_warnings": seal_ev.warnings if seal_ev else []
        }

        return PackagingFingerprint(
            product_identity=identity_slot,
            visual=visual_slot,
            text=text_slot,
            machine_readable=machine_slot,
            packaging=packaging_slot,
            regions=regions,
            version=PackagingFingerprintEngine.VERSION,
            created_at=datetime.utcnow().isoformat()
        )
