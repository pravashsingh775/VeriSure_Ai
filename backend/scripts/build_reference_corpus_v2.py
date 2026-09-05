import asyncio
import hashlib
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal, init_db
from backend.app.curation.duplicate_detector import DuplicateDetector, compute_perceptual_hashes, compute_sha256
from backend.app.curation.feature_pipeline import ReferenceFeatureExtractionPipeline
from backend.app.curation.quality_engine import PackagingQualityEngine10D
from backend.app.curation.variant_validator import VariantValidator
from backend.app.curation.version_detector import PackagingVersionAndPairingEngine
from backend.app.curation.view_classifier import PackagingViewClassifier
from backend.app.models.brand import Brand
from backend.app.models.dataset import Dataset, DatasetSample, DatasetVersion
from backend.app.models.packaging import PackagingVersion
from backend.app.models.product import Product, ProductPackSize, ProductVariant
from backend.app.models.reference import ReferenceFeature, ReferenceFingerprint, ReferenceImage

# Online Verified Level 2 Open Food Facts Packaging Sources
OFFLINE_CANDIDATE_URLS = [
    {
        "url": "https://images.openfoodfacts.org/images/products/890/126/226/0114/1.jpg",
        "expected_variant": "AMUL_GOLD",
        "barcode": "8901262260114",
        "pack_size": "1L",
        "source_type": "AUTHORIZED_SOURCE",
        "source_domain": "openfoodfacts.org",
        "license_status": "CC_BY_SA_3_0"
    },
    {
        "url": "https://images.openfoodfacts.org/images/products/890/126/226/0114/2.jpg",
        "expected_variant": "AMUL_GOLD",
        "barcode": "8901262260114",
        "pack_size": "1L",
        "source_type": "AUTHORIZED_SOURCE",
        "source_domain": "openfoodfacts.org",
        "license_status": "CC_BY_SA_3_0"
    },
    {
        "url": "https://images.openfoodfacts.org/images/products/890/126/226/0114/3.jpg",
        "expected_variant": "AMUL_GOLD",
        "barcode": "8901262260114",
        "pack_size": "1L",
        "source_type": "AUTHORIZED_SOURCE",
        "source_domain": "openfoodfacts.org",
        "license_status": "CC_BY_SA_3_0"
    },
    {
        "url": "https://images.openfoodfacts.org/images/products/890/126/226/0114/4.jpg",
        "expected_variant": "AMUL_GOLD",
        "barcode": "8901262260114",
        "pack_size": "1L",
        "source_type": "AUTHORIZED_SOURCE",
        "source_domain": "openfoodfacts.org",
        "license_status": "CC_BY_SA_3_0"
    },
    {
        "url": "https://images.openfoodfacts.org/images/products/890/126/226/0091/1.jpg",
        "expected_variant": "AMUL_TAAZA",
        "barcode": "8901262260091",
        "pack_size": "1L",
        "source_type": "AUTHORIZED_SOURCE",
        "source_domain": "openfoodfacts.org",
        "license_status": "CC_BY_SA_3_0"
    },
    {
        "url": "https://images.openfoodfacts.org/images/products/890/126/226/0091/2.jpg",
        "expected_variant": "AMUL_TAAZA",
        "barcode": "8901262260091",
        "pack_size": "1L",
        "source_type": "AUTHORIZED_SOURCE",
        "source_domain": "openfoodfacts.org",
        "license_status": "CC_BY_SA_3_0"
    },
    {
        "url": "https://images.openfoodfacts.org/images/products/890/126/215/0217/1.jpg",
        "expected_variant": "AMUL_TAAZA",
        "barcode": "8901262150217",
        "pack_size": "500ml",
        "source_type": "AUTHORIZED_SOURCE",
        "source_domain": "openfoodfacts.org",
        "license_status": "CC_BY_SA_3_0"
    },
    {
        "url": "https://images.openfoodfacts.org/images/products/890/126/215/0217/2.jpg",
        "expected_variant": "AMUL_TAAZA",
        "barcode": "8901262150217",
        "pack_size": "500ml",
        "source_type": "AUTHORIZED_SOURCE",
        "source_domain": "openfoodfacts.org",
        "license_status": "CC_BY_SA_3_0"
    },
    {
        "url": "https://images.openfoodfacts.org/images/products/890/126/215/0217/3.jpg",
        "expected_variant": "AMUL_TAAZA",
        "barcode": "8901262150217",
        "pack_size": "500ml",
        "source_type": "AUTHORIZED_SOURCE",
        "source_domain": "openfoodfacts.org",
        "license_status": "CC_BY_SA_3_0"
    },
    {
        "url": "https://images.openfoodfacts.org/images/products/890/126/215/0217/4.jpg",
        "expected_variant": "AMUL_TAAZA",
        "barcode": "8901262150217",
        "pack_size": "500ml",
        "source_type": "AUTHORIZED_SOURCE",
        "source_domain": "openfoodfacts.org",
        "license_status": "CC_BY_SA_3_0"
    }
]


async def build_reference_corpus_v2():
    print("=" * 70)
    print("VERISURE AI — AUTOMATED REFERENCE CORPUS V2 INGESTION PIPELINE")
    print("=" * 70)

    # Setup directories
    base_dir = Path(r"C:\Users\PRAVASH\Desktop\VeriSure_Ai")
    ref_v2_dir = base_dir / "data" / "storage" / "references_v2"
    neg_dir = base_dir / "data" / "storage" / "negative_samples"
    ref_v2_dir.mkdir(parents=True, exist_ok=True)
    neg_dir.mkdir(parents=True, exist_ok=True)

    # Initialize engines
    dedup = DuplicateDetector(duplicate_threshold=4, near_duplicate_threshold=10)
    quality_engine = PackagingQualityEngine10D()
    variant_validator = VariantValidator()
    view_classifier = PackagingViewClassifier()
    version_engine = PackagingVersionAndPairingEngine()
    feature_pipeline = ReferenceFeatureExtractionPipeline()

    # 1. Index Reference Corpus V1 as immutable baseline
    v1_manifest_path = base_dir / "data" / "reference_corpus_v1_manifest.json"
    if v1_manifest_path.exists():
        with open(v1_manifest_path, "r", encoding="utf-8") as f:
            v1_data = json.load(f)
            for rec in v1_data.get("records", []):
                v1_img_path = base_dir / "data" / "storage" / rec["relative_path"]
                if v1_img_path.exists():
                    img = cv2.imread(str(v1_img_path))
                    if img is not None:
                        hsh = compute_perceptual_hashes(img)
                        dedup.register_canonical(
                            image_id=rec["image_id"],
                            sha256_hash=rec["sha256"],
                            hashes=hsh,
                            metadata={"corpus": "V1", "variant": rec["product_name"]}
                        )
        print(f"[V1 BASELINE] Registered {len(dedup.sha_index)} immutable V1 reference hashes.")

    # 2. Download and curate online candidates
    headers = {"User-Agent": "VeriSureAI-DatasetCurator/2.0 (contact@verisure.ai)"}
    downloaded_candidates = []

    print("\n[DISCOVERY] Ingesting verified candidate images...")
    for item in OFFLINE_CANDIDATE_URLS:
        url = item["url"]
        fname = f"off_{item['barcode']}_{url.split('/')[-1]}"
        dest = ref_v2_dir / fname

        if not dest.exists():
            try:
                r = requests.get(url, headers=headers, timeout=12)
                if r.status_code == 200 and len(r.content) > 10000:
                    with open(dest, "wb") as f:
                        f.write(r.content)
                    print(f"  Downloaded: {fname} ({len(r.content)} bytes)")
                else:
                    print(f"  [WARN] Failed to download {url}: Status {r.status_code}")
                    continue
            except Exception as e:
                print(f"  [WARN] Download error {url}: {e}")
                continue

        downloaded_candidates.append({
            "source_path": str(dest),
            "filename": fname,
            "source_url": url,
            "source_domain": item["source_domain"],
            "source_type": item["source_type"],
            "license_status": item["license_status"],
            "provenance_status": "AUTHORIZED_SOURCE",
            "declared_barcode": item.get("barcode"),
            "pack_size": item.get("pack_size", "1L")
        })

    # Also ingest unique physical packaging photos from raw_scans
    raw_dir = base_dir / "data" / "storage" / "raw_scans"
    if raw_dir.exists():
        for p in raw_dir.glob("*.png"):
            # Select key high-res captures
            if any(k in p.name.lower() for k in ["amul_milk", "fop-taaza", "amul_tazza", "mother_dairy", "diagram"]):
                downloaded_candidates.append({
                    "source_path": str(p),
                    "filename": p.name,
                    "source_url": f"local://raw_scans/{p.name}",
                    "source_domain": "verisure_local_capture",
                    "source_type": "VERIFIED_EXTERNAL",
                    "license_status": "INTERNAL_PROJECT",
                    "provenance_status": "VERIFIED_EXTERNAL",
                    "declared_barcode": None,
                    "pack_size": "500ml"
                })

    # 3. Process each candidate through Curation & Feature Pipeline
    v2_approved_records: List[Dict[str, Any]] = []
    negative_records: List[Dict[str, Any]] = []
    duplicate_count = 0
    rejected_count = 0

    idx = 1
    for cand in downloaded_candidates:
        src = cand["source_path"]
        img = cv2.imread(src)
        if img is None or img.size == 0:
            continue

        sha = compute_sha256(src)
        hashes = compute_perceptual_hashes(img)

        # Duplicate Check against V1 and earlier V2
        is_dup, is_exact, canon_id, dist = dedup.check_duplicate(sha, hashes["phash"])
        if is_dup:
            duplicate_count += 1
            dedup.record_duplicate(
                canonical_id=canon_id,
                source_url=cand["source_url"],
                source_domain=cand["source_domain"],
                source_type=cand["source_type"],
                sha256_hash=sha,
                distance=dist
            )
            print(f"  [DEDUP] Skipped duplicate of {canon_id} (Dist: {dist}): {cand['filename']}")
            continue

        # 10-Dimension Quality Assessment
        qual_res = quality_engine.evaluate(img)
        if not qual_res.usable:
            rejected_count += 1
            print(f"  [REJECT] Low quality ({qual_res.overall_quality:.2f}, {qual_res.quality_status}): {cand['filename']}")
            continue

        # OCR & Barcode Extraction for Variant/View Determination
        # Run temporary barcode and OCR
        from backend.app.ai.codes.barcode import BarcodeAnalyzer
        from backend.app.ai.ocr.engine import OCREngine
        bc_res = BarcodeAnalyzer().analyze(img)
        detected_bc = bc_res.features.get("decoded_value") if bc_res.availability else cand.get("declared_barcode")
        ocr_text, ocr_conf, _ = OCREngine().extract_text(img)

        # Multi-signal Variant Validation
        variant, v_conf, v_signals = variant_validator.validate(
            img_bgr=img,
            ocr_text=ocr_text,
            barcode=detected_bc,
            source_url=cand["source_url"]
        )

        # Route Negative Samples (Competitor brands & Diagrams)
        if variant in ["OTHER_BRAND", "NON_PRODUCT_IMAGE"]:
            neg_fname = f"neg_{cand['filename']}"
            neg_dst = neg_dir / neg_fname
            shutil.copy2(src, neg_dst)
            negative_records.append({
                "sample_id": f"NEG-{len(negative_records)+1:03d}",
                "category": variant,
                "label": variant,
                "provenance_status": "VERIFIED_EXTERNAL",
                "filename": neg_fname,
                "relative_path": f"negative_samples/{neg_fname}",
                "sha256": sha,
                "signals": v_signals,
                "source_url": cand["source_url"]
            })
            print(f"  [NEGATIVE] Routed to negative corpus ({variant}): {cand['filename']}")
            continue

        if variant == "UNKNOWN":
            print(f"  [INCONCLUSIVE] Unable to verify variant: {cand['filename']}")
            continue

        # View Classification
        view_type, view_conf = view_classifier.classify_view(
            img_bgr=img,
            ocr_text=ocr_text,
            barcode_detected=detected_bc is not None
        )

        # Packaging Version Detection
        pkg_version = version_engine.detect_version(
            ocr_text=ocr_text,
            barcode=detected_bc,
            has_qr="http" in ocr_text.lower() or "qr" in ocr_text.lower()
        )

        # Full 12-Engine Evidence & Feature Extraction
        features_out = feature_pipeline.extract_reference_features(
            img_bgr=img,
            variant=variant,
            packaging_version=pkg_version,
            view_type=view_type
        )

        # Copy to official references_v2 folder
        v2_image_id = f"{variant.replace('AMUL_', '')}-V2-{idx:03d}"
        v2_filename = f"{v2_image_id.lower()}_{view_type.lower()}.png"
        v2_dest = ref_v2_dir / v2_filename
        cv2.imwrite(str(v2_dest), img)

        # Register in Duplicate Detector
        dedup.register_canonical(
            image_id=v2_image_id,
            sha256_hash=sha,
            hashes=hashes,
            metadata={"corpus": "V2", "variant": variant, "view": view_type}
        )

        record = {
            "image_id": v2_image_id,
            "product_name": variant.replace("_", " ").title(),
            "variant_name": "Full Cream Milk" if "GOLD" in variant else ("Toned Milk" if "TAAZA" in variant else "Standardised Milk"),
            "variant": variant,
            "pack_size": cand.get("pack_size", "1L"),
            "pack_type": "POUCH",
            "view_type": view_type,
            "packaging_version": pkg_version,
            "source_url": cand["source_url"],
            "source_domain": cand["source_domain"],
            "source_type": cand["source_type"],
            "provenance_status": cand["provenance_status"],
            "verification_status": "APPROVED",
            "license_status": cand["license_status"],
            "filename": v2_filename,
            "relative_path": f"references_v2/{v2_filename}",
            "absolute_path": str(v2_dest),
            "sha256": sha,
            "hashes": hashes,
            "dimensions": f"{img.shape[1]}x{img.shape[0]}",
            "file_size_bytes": v2_dest.stat().st_size,
            "quality_score": qual_res.overall_quality,
            "quality_status": qual_res.quality_status,
            "blur_score": qual_res.blur_score,
            "detected_barcode": detected_bc,
            "ocr_excerpt": ocr_text[:120].replace("\n", " "),
            "fingerprint": features_out["fingerprint"],
            "individual_features": features_out["individual_features"],
            "duplicate_sources": dedup.duplicate_sources.get(v2_image_id, [])
        }

        v2_approved_records.append(record)
        print(f"  [APPROVED] Ingested {v2_image_id} -> {v2_filename} [{variant}, {view_type}, Quality: {qual_res.overall_quality:.3f}]")
        idx += 1

    # 4. Front/Back Pairing Analysis
    pairs = version_engine.pair_front_and_back(v2_approved_records)
    print(f"\n[PAIRING] Discovered {len(pairs)} verified Front/Back packaging pairs.")

    # 5. Database Synchronization
    print("\n[DATABASE] Synchronizing Reference Corpus V2 with PostgreSQL...")
    await init_db()

    async with AsyncSessionLocal() as session:
        amul_brand = (await session.execute(select(Brand).where(Brand.code == "AMUL"))).scalar_one_or_none()
        if not amul_brand:
            raise RuntimeError("Brand AMUL not found in database!")

        # Create or fetch Dataset: VERISURE_REFERENCE_CORPUS
        ds = (await session.execute(select(Dataset).where(Dataset.name == "VERISURE_REFERENCE_CORPUS"))).scalar_one_or_none()
        if not ds:
            ds = Dataset(
                name="VERISURE_REFERENCE_CORPUS",
                description="Official Reference Packaging Corpus for Amul Dairy verification.",
                domain_tag="AMUL_DAIRY"
            )
            session.add(ds)
            await session.flush()

        # Create DatasetVersion v2.0.0
        dsv2 = (await session.execute(
            select(DatasetVersion).where((DatasetVersion.dataset_id == ds.id) & (DatasetVersion.version_tag == "v2.0.0"))
        )).scalar_one_or_none()
        if not dsv2:
            dsv2 = DatasetVersion(
                dataset_id=ds.id,
                version_tag="v2.0.0",
                split_strategy="PACKAGE_AND_SESSION_ISOLATED",
                train_count=len(v2_approved_records),
                val_count=0,
                test_count=0,
                is_locked=True,
                metadata_json={
                    "created_at": datetime.utcnow().isoformat(),
                    "total_images": len(v2_approved_records),
                    "negative_count": len(negative_records),
                    "pair_count": len(pairs)
                }
            )
            session.add(dsv2)
            await session.flush()

        for rec in v2_approved_records:
            prod_name = rec["product_name"]
            var_name = rec["variant_name"]
            p_size = rec["pack_size"]
            p_type = rec["pack_type"]

            # 1. Product
            prod = (await session.execute(
                select(Product).where((Product.name == prod_name) & (Product.brand_id == amul_brand.id))
            )).scalar_one_or_none()
            if not prod:
                prod = Product(brand_id=amul_brand.id, name=prod_name, category="DAIRY", is_active=True)
                session.add(prod)
                await session.flush()

            # 2. ProductVariant
            variant_obj = (await session.execute(
                select(ProductVariant).where((ProductVariant.product_id == prod.id) & (ProductVariant.variant_name == var_name))
            )).scalar_one_or_none()
            if not variant_obj:
                variant_obj = ProductVariant(product_id=prod.id, variant_name=var_name)
                session.add(variant_obj)
                await session.flush()

            # 3. ProductPackSize
            pack_size_obj = (await session.execute(
                select(ProductPackSize).where(
                    (ProductPackSize.variant_id == variant_obj.id) &
                    (ProductPackSize.pack_size == p_size) &
                    (ProductPackSize.pack_type == p_type)
                )
            )).scalar_one_or_none()
            if not pack_size_obj:
                pack_size_obj = ProductPackSize(variant_id=variant_obj.id, pack_size=p_size, pack_type=p_type, net_quantity=p_size)
                session.add(pack_size_obj)
                await session.flush()

            # 4. PackagingVersion (V2)
            pkg_ver = (await session.execute(
                select(PackagingVersion).where(
                    (PackagingVersion.pack_size_id == pack_size_obj.id) &
                    (PackagingVersion.version_code == "V2")
                )
            )).scalar_one_or_none()
            if not pkg_ver:
                pkg_ver = PackagingVersion(
                    pack_size_id=pack_size_obj.id,
                    version_code="V2",
                    status="ACTIVE",
                    expected_barcode=rec["detected_barcode"],
                    expected_fssai="10012021000071",
                    notes="Reference Corpus V2 active packaging iteration"
                )
                session.add(pkg_ver)
                await session.flush()

            # 5. ReferenceImage
            existing_ref = (await session.execute(
                select(ReferenceImage).where(ReferenceImage.image_path == rec["relative_path"])
            )).scalar_one_or_none()
            if not existing_ref:
                ref_img = ReferenceImage(
                    packaging_version_id=pkg_ver.id,
                    view_type=rec["view_type"],
                    image_path=rec["relative_path"],
                    original_filename=rec["filename"],
                    source_type=rec["source_type"],
                    source_document=rec["source_url"],
                    captured_at=datetime.utcnow(),
                    trust_level=0.95,
                    approval_status="APPROVED",
                    verification_status="VERIFIED",
                    uploaded_by="CURATION_PIPELINE_V2",
                    approved_by="CURATION_PIPELINE_V2",
                    approved_at=datetime.utcnow()
                )
                session.add(ref_img)
                await session.flush()
                ref_img_id = ref_img.id
            else:
                ref_img_id = existing_ref.id

            # 6. ReferenceFeatures (12 Engine blocks)
            for f_type, f_data in rec["individual_features"].items():
                f_obj = ReferenceFeature(
                    reference_image_id=ref_img_id,
                    feature_type=f_type,
                    feature_data=f_data
                )
                session.add(f_obj)

            # 7. ReferenceFingerprint
            fp_obj = (await session.execute(
                select(ReferenceFingerprint).where(ReferenceFingerprint.packaging_version_id == pkg_ver.id)
            )).scalar_one_or_none()
            if not fp_obj:
                fp_obj = ReferenceFingerprint(
                    packaging_version_id=pkg_ver.id,
                    model_version="v2.0",
                    fingerprint_json=rec["fingerprint"]
                )
                session.add(fp_obj)

            # 8. DatasetSample linkage
            samp = DatasetSample(
                dataset_version_id=dsv2.id,
                image_path=rec["relative_path"],
                label="GENUINE",
                split="TRAIN",
                package_id=rec["image_id"],
                capture_session_id="CORPUS_V2_INGESTION"
            )
            session.add(samp)

        await session.commit()
        print("[DATABASE] Reference Corpus V2 successfully synchronized in PostgreSQL.")

    # 6. Write Reference Corpus V2 Manifest
    manifest_data = {
        "title": "VeriSure AI — Reference Corpus V2 Manifest",
        "dataset_version": "v2.0.0",
        "created_at": datetime.utcnow().isoformat(),
        "total_approved_references": len(v2_approved_records),
        "total_negative_samples": len(negative_records),
        "total_front_back_pairs": len(pairs),
        "duplicate_occurrences_filtered": duplicate_count,
        "low_quality_rejected": rejected_count,
        "products_distribution": {
            "Amul Gold": sum(1 for x in v2_approved_records if "GOLD" in x["variant"]),
            "Amul Taaza": sum(1 for x in v2_approved_records if "TAAZA" in x["variant"]),
            "Amul Shakti": sum(1 for x in v2_approved_records if "SHAKTI" in x["variant"])
        },
        "view_distribution": {
            "FRONT": sum(1 for x in v2_approved_records if x["view_type"] == "FRONT"),
            "BACK": sum(1 for x in v2_approved_records if x["view_type"] == "BACK"),
            "DETAIL": sum(1 for x in v2_approved_records if x["view_type"] == "DETAIL"),
            "SEAL": sum(1 for x in v2_approved_records if x["view_type"] == "SEAL")
        },
        "pairs": pairs,
        "approved_records": v2_approved_records,
        "negative_records": negative_records
    }

    manifest_file = base_dir / "data" / "reference_corpus_v2_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"\n[OUTPUT] Reference Corpus V2 Manifest written to {manifest_file}")
    print("INGESTION PIPELINE COMPLETED SUCCESSFULLY.")
    return manifest_data


if __name__ == "__main__":
    asyncio.run(build_reference_corpus_v2())

