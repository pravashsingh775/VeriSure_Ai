from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.models.packaging import PackagingVersion
from backend.app.models.product import Product, ProductPackSize, ProductVariant
from backend.app.models.reference import ReferenceImage


class ReferenceRetriever:
    """
    Hierarchically filters and retrieves candidate genuine reference templates.
    Brand -> Product -> Pack Size -> Packaging Version (Active or Historical/Deprecated) -> View Angle.

    Adheres to Scientific Reference Integrity:
    1. Historical/Deprecated packaging versions are supported and evaluated with full authenticity.
       An authentic older package is never marked counterfeit solely because a newer version is active.
    2. Synthetic test stubs (source_type == "SYNTHETIC_TEST_STUB") are NEVER used as production reference templates.
    """
    @staticmethod
    async def retrieve_candidates(
        db: AsyncSession,
        detected_text: str,
        detected_barcode: Optional[str] = None,
        view_type: str = "FRONT",
        crop_bgr: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        import cv2
        import numpy as np

        # Fetch all products with variants, pack sizes, and packaging versions
        stmt = (
            select(Product)
            .options(
                selectinload(Product.variants)
                .selectinload(ProductVariant.pack_sizes)
                .selectinload(ProductPackSize.packaging_versions)
                .selectinload(PackagingVersion.reference_images)
            )
        )
        result = await db.execute(stmt)
        products = result.scalars().all()

        candidates: List[Dict[str, Any]] = []
        text_upper = detected_text.upper() if detected_text else ""

        # Brand-specific variant and multi-lingual keywords
        brand_keywords = {
            "Amul Gold": ["GOLD", "गोल्ड", "MILKY", "FULL CREAM", "MILKY MILK", "फुल क्रीम"],
            "Amul Taaza": ["TAAZA", "ताजा", "TONED", "T-SPECIAL", "टोन्ड"],
            "Amul Shakti": ["SHAKTI", "शक्ति", "STANDARDISED", "HOMOGENISED", "मानकीकृत"],
        }

        # Color cues from packaging crop
        dominant_color = None
        if crop_bgr is not None and getattr(crop_bgr, "size", 0) > 0:
            try:
                hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
                non_white = (hsv[:, :, 1] > 25) & (hsv[:, :, 2] > 40)
                hues = hsv[:, :, 0][non_white]
                if len(hues) > 100:
                    total_h = float(len(hues))
                    r_pct = float(np.sum((hues < 15) | (hues > 165))) / total_h
                    b_pct = float(np.sum((hues >= 95) & (hues <= 135))) / total_h
                    g_pct = float(np.sum((hues >= 35) & (hues <= 85))) / total_h
                    if r_pct > 0.30 and r_pct > b_pct and r_pct > g_pct:
                        dominant_color = "Amul Gold"
                    elif b_pct > 0.30 and b_pct > r_pct and b_pct > g_pct:
                        dominant_color = "Amul Taaza"
                    elif g_pct > 0.30 and g_pct > r_pct and g_pct > b_pct:
                        dominant_color = "Amul Shakti"
            except Exception:
                pass

        for prod in products:
            for variant in prod.variants:
                for ps in variant.pack_sizes:
                    for pv in ps.packaging_versions:
                        # Allow ACTIVE and DEPRECATED (historical) packaging versions
                        # Exclude only unapproved drafts and archived non-production templates
                        if pv.status not in ["ACTIVE", "DEPRECATED", "APPROVED"]:
                            continue

                        # Base relevance score
                        match_score = 0.40

                        # 1. Barcode match is a definitive candidate indicator
                        if detected_barcode and pv.expected_barcode:
                            if detected_barcode == pv.expected_barcode:
                                match_score += 0.50
                            else:
                                match_score -= 0.30

                        # 2. Text token & keyword matches (English and Devanagari)
                        if prod.name.upper() in text_upper:
                            match_score += 0.25
                        if variant.variant_name.upper() in text_upper:
                            match_score += 0.20
                        if ps.pack_size.upper() in text_upper:
                            match_score += 0.15

                        for kw in brand_keywords.get(prod.name, []):
                            if kw in text_upper:
                                match_score += 0.35
                                break

                        # 3. Visual color signature cues
                        if dominant_color and prod.name == dominant_color:
                            match_score += 0.30

                        # Strict Reference Selection:
                        # MUST be APPROVED and MUST NOT be a SYNTHETIC_TEST_STUB
                        trusted_images = [
                            img for img in pv.reference_images
                            if img.approval_status == "APPROVED"
                            and img.source_type != "SYNTHETIC_TEST_STUB"
                        ]

                        ref_img = next((img for img in trusted_images if img.view_type == view_type), None)
                        if not ref_img and trusted_images:
                            ref_img = trusted_images[0]

                        # Fallback: if this specific packaging version has no reference image,
                        # look up an approved reference image from the same variant/product
                        # (Amul milk front packaging design is identical across pack sizes)
                        if not ref_img:
                            for other_ps in variant.pack_sizes:
                                for other_pv in other_ps.packaging_versions:
                                    other_trusted = [
                                        img for img in other_pv.reference_images
                                        if img.approval_status == "APPROVED"
                                        and img.source_type != "SYNTHETIC_TEST_STUB"
                                    ]
                                    fallback_img = next((img for img in other_trusted if img.view_type == view_type), None)
                                    if fallback_img:
                                        ref_img = fallback_img
                                        break
                                    elif other_trusted and not ref_img:
                                        ref_img = other_trusted[0]
                                if ref_img:
                                    break

                        # Packaging versions that directly or via fallback possess reference images rank higher
                        if ref_img is not None:
                            match_score += 0.20
                        else:
                            match_score -= 0.20

                        match_score = min(1.0, max(0.1, match_score))
                        is_historical = (pv.status == "DEPRECATED")

                        candidates.append({
                            "product_id": prod.id,
                            "product_name": prod.name,
                            "variant_id": variant.id,
                            "variant_name": variant.variant_name,
                            "pack_size_id": ps.id,
                            "pack_size": ps.pack_size,
                            "packaging_version_id": pv.id,
                            "version_code": pv.version_code,
                            "packaging_version_status": pv.status,
                            "is_historical": is_historical,
                            "effective_start_date": pv.effective_start_date.isoformat() if pv.effective_start_date else None,
                            "effective_end_date": pv.effective_end_date.isoformat() if pv.effective_end_date else None,
                            "expected_barcode": pv.expected_barcode,
                            "expected_fssai": pv.expected_fssai,
                            "expected_mrp": pv.expected_mrp,
                            "reference_image_id": ref_img.id if ref_img else None,
                            "reference_image_path": ref_img.image_path if ref_img else None,
                            "reference_source_type": ref_img.source_type if ref_img else None,
                            "reference_trust_level": ref_img.trust_level if ref_img else 0.0,
                            "retrieval_score": round(match_score, 3)
                        })

        # Sort candidates descending by score
        candidates.sort(key=lambda x: x["retrieval_score"], reverse=True)
        return candidates
