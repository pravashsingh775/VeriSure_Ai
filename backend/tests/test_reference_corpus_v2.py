import json
from pathlib import Path

import cv2
import numpy as np

from backend.app.curation.duplicate_detector import DuplicateDetector, compute_perceptual_hashes, compute_sha256
from backend.app.curation.feature_pipeline import ReferenceFeatureExtractionPipeline
from backend.app.curation.quality_engine import PackagingQualityEngine10D
from backend.app.curation.rag_knowledge_base import PackagingRAGKnowledgeBase
from backend.app.curation.variant_validator import VariantValidator
from backend.app.curation.view_classifier import PackagingViewClassifier


def test_duplicate_detector_exact_and_perceptual():
    detector = DuplicateDetector(duplicate_threshold=4, near_duplicate_threshold=10)

    # Packaging reference image with rich visual features
    ref_file = Path("data/storage/references/media_1788440125203.jpg")
    if ref_file.exists():
        img1 = cv2.imread(str(ref_file))
    else:
        img1 = np.full((400, 400, 3), 150, dtype=np.uint8)
        cv2.putText(img1, "AMUL GOLD", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 220), 3)
        cv2.putText(img1, "MILK POUCH", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)

    sha1 = compute_sha256(cv2.imencode(".png", img1)[1].tobytes())
    hashes1 = compute_perceptual_hashes(img1)

    detector.register_canonical("CANON-001", sha1, hashes1, {"variant": "AMUL_GOLD"})

    # Exact duplicate test
    is_dup, is_exact, canon_id, dist = detector.check_duplicate(sha1, hashes1["phash"])
    assert is_dup is True
    assert is_exact is True
    assert canon_id == "CANON-001"
    assert dist == 0

    # Perceptual duplicate test (JPEG re-compression)
    jpg_bytes = cv2.imencode(".jpg", img1, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tobytes()
    img_jpg = cv2.imdecode(np.frombuffer(jpg_bytes, np.uint8), cv2.IMREAD_COLOR)
    sha_jpg = compute_sha256(jpg_bytes)
    hashes_jpg = compute_perceptual_hashes(img_jpg)

    is_dup2, is_exact2, canon_id2, dist2 = detector.check_duplicate(sha_jpg, hashes_jpg["phash"])
    assert is_dup2 is True
    assert is_exact2 is False
    assert canon_id2 == "CANON-001"
    assert dist2 <= 4

    # Near-duplicate test (subtle brightness change, distance <= 10)
    img2 = cv2.add(img1, np.full_like(img1, 5))
    hashes2 = compute_perceptual_hashes(img2)
    is_near, near_id, near_dist = detector.is_near_duplicate(hashes2["phash"])
    assert is_near is True
    assert near_id == "CANON-001"
    assert near_dist <= 10

    # Completely different image test
    img3 = np.zeros((300, 300, 3), dtype=np.uint8)
    for i in range(0, 300, 20):
        cv2.line(img3, (0, i), (300, i), (255, 255, 255), 2)
    sha3 = compute_sha256(cv2.imencode(".png", img3)[1].tobytes())
    hashes3 = compute_perceptual_hashes(img3)

    is_dup3, _, _, dist3 = detector.check_duplicate(sha3, hashes3["phash"])
    assert is_dup3 is False
    assert dist3 > 4


def test_quality_engine_10d_dimensions_and_scoring():
    engine = PackagingQualityEngine10D(min_dim_threshold=250)

    # Sharp, well-lit synthetic packaging image
    good_img = np.full((600, 500, 3), 180, dtype=np.uint8)
    cv2.putText(good_img, "AMUL GOLD", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 180), 3)
    cv2.putText(good_img, "Full Cream Milk", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)

    good_res = engine.evaluate(good_img)
    assert good_res.usable is True
    assert good_res.overall_quality >= 0.60
    assert good_res.quality_status in ["EXCELLENT", "GOOD", "ACCEPTABLE"]
    assert good_res.width == 500
    assert good_res.height == 600

    # Blurry image
    blurry_img = cv2.GaussianBlur(good_img, (35, 35), 10.0)
    blur_res = engine.evaluate(blurry_img)
    assert blur_res.blur_score < good_res.blur_score

    # Tiny reject image (< 200px)
    tiny_img = cv2.resize(good_img, (150, 150))
    tiny_res = engine.evaluate(tiny_img)
    assert tiny_res.usable is False


def test_variant_validator_amul_vs_competitor_vs_diagram():
    validator = VariantValidator()

    # Amul Gold with barcode
    img_gold = np.full((400, 400, 3), 150, dtype=np.uint8)
    var_gold, conf_gold, _ = validator.validate(img_gold, "Amul Gold Pasteurised Full Cream Milk", barcode="8901262260114")
    assert var_gold == "AMUL_GOLD"
    assert conf_gold >= 0.70

    # Amul Taaza with barcode
    img_taaza = np.full((400, 400, 3), 150, dtype=np.uint8)
    var_taaza, conf_taaza, _ = validator.validate(img_taaza, "Amul Taaza Toned Milk", barcode="8901262260091")
    assert var_taaza == "AMUL_TAAZA"
    assert conf_taaza >= 0.70

    # Competitor brand: Mother Dairy
    img_other = np.full((400, 400, 3), 150, dtype=np.uint8)
    var_other, conf_other, sigs_other = validator.validate(img_other, "Mother Dairy Full Cream Milk 500ml")
    assert var_other == "OTHER_BRAND"
    assert conf_other == 0.99
    assert sigs_other["detected_competitor"] == "mother dairy"

    # Non-product diagram: Architecture diagram
    diagram_img = np.full((600, 800, 3), 250, dtype=np.uint8)
    for i in range(10):
        cv2.rectangle(diagram_img, (50 + i * 60, 50), (90 + i * 60, 100), (0, 0, 0), 2)
    var_diag, conf_diag, _ = validator.validate(diagram_img, "System Architecture Diagram API Gateway Component Database")
    assert var_diag == "NON_PRODUCT_IMAGE"
    assert conf_diag >= 0.90


def test_view_classifier_front_back_nutrition():
    classifier = PackagingViewClassifier()

    dummy_img = np.full((500, 400, 3), 160, dtype=np.uint8)

    # Back view with barcode and FSSAI
    view_back, conf_back = classifier.classify_view(
        dummy_img,
        ocr_text="Marketed by GCMMF Anand. FSSAI Lic No 10012021000071 Nutritional Information per 100ml",
        barcode_detected=True
    )
    assert view_back == "BACK"
    assert conf_back >= 0.70

    # Front view with branding and no barcode
    view_front, conf_front = classifier.classify_view(
        dummy_img,
        ocr_text="Amul Gold Full Cream Milk Rich & Creamy Pasteurised",
        barcode_detected=False
    )
    assert view_front == "FRONT"
    assert conf_front >= 0.60

    # Nutrition macro panel
    view_nut, conf_nut = classifier.classify_view(
        dummy_img,
        ocr_text="Nutritional Information per 100 ml Energy kcal Total Fat Carbohydrate",
        barcode_detected=False
    )
    assert view_nut == "NUTRITION"
    assert conf_nut >= 0.80


def test_feature_pipeline_12_engines_extraction():
    pipeline = ReferenceFeatureExtractionPipeline()

    img = np.full((500, 400, 3), 200, dtype=np.uint8)
    cv2.circle(img, (200, 150), 60, (0, 0, 200), -1)
    cv2.putText(img, "AMUL", (140, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

    out = pipeline.extract_reference_features(img, variant="AMUL_GOLD", packaging_version="V2", view_type="FRONT")

    assert "fingerprint" in out
    assert "individual_features" in out

    fp = out["fingerprint"]
    assert fp["variant"] == "AMUL_GOLD"
    assert fp["packaging_version"] == "V2"
    assert fp["view"] == "FRONT"

    # Verify all 12 feature engines are present
    expected_engines = [
        "logo_features", "layout_features", "colour_features", "typography_features",
        "texture_features", "shape_features", "seal_features", "print_features",
        "ocr_features", "barcode_features", "qr_features", "certification_features"
    ]
    for engine_key in expected_engines:
        assert engine_key in fp, f"Missing {engine_key} in packaging fingerprint"


def test_rag_knowledge_base_retrieval_and_disclaimer():
    kb = PackagingRAGKnowledgeBase(Path("data/rag_knowledge"))

    # Test Gold specification query
    gold_spec = kb.query_product_spec("AMUL_GOLD")
    assert gold_spec["variant"] == "AMUL_GOLD"
    assert "disclaimer" in gold_spec
    assert "NEVER override" in gold_spec["disclaimer"]
    spec_data = gold_spec["specification"]
    assert spec_data.get("brand") == "Amul"
    assert spec_data.get("composition", {}).get("minimum_milk_fat") == "6.0%"

    # Test Taaza specification query
    taaza_spec = kb.query_product_spec("AMUL_TAAZA")
    assert taaza_spec["specification"].get("composition", {}).get("minimum_milk_fat") == "3.0%"

    # Test Shakti specification query
    shakti_spec = kb.query_product_spec("AMUL_SHAKTI")
    assert shakti_spec["specification"].get("composition", {}).get("minimum_milk_fat") == "4.5%"

    # Test regulatory requirements query
    reg = kb.query_regulatory_requirements()
    assert "regulations" in reg
    assert "disclaimer" in reg
    assert "FSSAI" in json.dumps(reg)


def test_reference_corpus_v2_manifest_integrity():
    manifest_path = Path("data/reference_corpus_v2_manifest.json")
    assert manifest_path.exists(), "Reference Corpus V2 manifest does not exist"

    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("dataset_version") == "v2.0.0"
    assert data.get("total_approved_references") > 0
    assert len(data.get("approved_records", [])) == data["total_approved_references"]

    # Verify zero duplicate SHA-256 hashes among approved references
    shas = [r["sha256"] for r in data["approved_records"]]
    assert len(shas) == len(set(shas)), "Found duplicate SHA-256 in approved records"

    # Verify that negative records exist and contain Mother Dairy or Diagrams
    neg_records = data.get("negative_records", [])
    assert len(neg_records) > 0
    labels = {r["label"] for r in neg_records}
    assert "OTHER_BRAND" in labels or "NON_PRODUCT_IMAGE" in labels

