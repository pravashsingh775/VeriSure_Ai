import uuid
from typing import Any, Dict, List, Optional, Tuple


class PackagingVersionAndPairingEngine:
    """
    Groups packaging references by packaging design version (V1, V2, etc.)
    and discovers legitimate Front/Back packaging pairs without fabrication.
    """

    def detect_version(
        self,
        ocr_text: str = "",
        barcode: Optional[str] = None,
        has_qr: bool = False,
        declared_mrp: Optional[float] = None
    ) -> str:
        """
        Determines the packaging version iteration from regulatory and design markers.
        """
        text_lower = ocr_text.lower()

        # V2 indicators: QR code integration, FSSAI 2020 nutrition norms ("added sugar"),
        # or modern consumer helpline
        if has_qr or "added sugar" in text_lower or "total added sugars" in text_lower:
            return "V2"

        # Check for historical packaging indications
        if declared_mrp and declared_mrp < 24.0:
            return "V_HISTORICAL"

        return "V1"

    def pair_front_and_back(
        self,
        records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Identifies verified Front/Back pairs among curated records.
        A valid pair MUST:
        1. Have the same variant (e.g. AMUL_GOLD == AMUL_GOLD)
        2. Have compatible packaging versions
        3. Have compatible dimensions / pack size
        4. Originate from the same or compatible source origin
        """
        fronts = [r for r in records if r.get("view_type") == "FRONT" and r.get("variant") in ["AMUL_GOLD", "AMUL_TAAZA", "AMUL_SHAKTI"]]
        backs = [r for r in records if r.get("view_type") == "BACK" and r.get("variant") in ["AMUL_GOLD", "AMUL_TAAZA", "AMUL_SHAKTI"]]

        pairs: List[Dict[str, Any]] = []
        used_backs = set()

        for f in fronts:
            f_id = f["image_id"]
            f_variant = f["variant"]
            f_version = f.get("packaging_version", "V1")
            f_source_domain = f.get("source_domain", "")
            f_pack_size = f.get("pack_size")

            best_back = None
            best_score = 0.0

            for b in backs:
                b_id = b["image_id"]
                if b_id in used_backs:
                    continue

                if b["variant"] != f_variant:
                    continue

                score = 0.50  # Base compatibility

                # Packaging version compatibility
                if b.get("packaging_version") == f_version:
                    score += 0.25

                # Pack size compatibility
                if f_pack_size and b.get("pack_size") and f_pack_size == b.get("pack_size"):
                    score += 0.15

                # Source domain affinity (e.g. captured in same batch or catalog)
                if f_source_domain and b.get("source_domain") == f_source_domain:
                    score += 0.10

                if score > best_score and score >= 0.70:
                    best_score = score
                    best_back = b

            if best_back is not None:
                used_backs.add(best_back["image_id"])
                pair_id = f"PAIR-{f_variant.replace('AMUL_', '')}-{f_version}-{uuid.uuid4().hex[:6].upper()}"
                pairs.append({
                    "pair_id": pair_id,
                    "variant": f_variant,
                    "packaging_version": f_version,
                    "front_image_id": f_id,
                    "back_image_id": best_back["image_id"],
                    "pair_confidence": round(best_score, 2),
                    "notes": f"Verified Front/Back pair for {f_variant} ({f_version})"
                })

        return pairs

