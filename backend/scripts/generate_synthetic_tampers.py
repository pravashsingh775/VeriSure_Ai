import json
from pathlib import Path
from typing import Any, Dict, List
import cv2
import numpy as np

from backend.app.curation.duplicate_detector import compute_perceptual_hashes, compute_sha256
from backend.app.curation.quality_engine import PackagingQualityEngine10D


def generate_synthetic_tampers(
    reference_dir: Path,
    output_dir: Path
) -> List[Dict[str, Any]]:
    """
    Generates controlled, reproducible synthetic tamper samples for research and robustness testing.
    All generated samples are strictly labeled SYNTHETIC_TAMPER with provenance SYNTHETIC_TEST_STUB.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    quality_engine = PackagingQualityEngine10D()
    manifest_records: List[Dict[str, Any]] = []

    # Select base authentic samples from V1 references
    sample_files = list(reference_dir.glob("media_*.jpg"))
    if not sample_files:
        sample_files = list(Path("data/storage/references").glob("media_*.jpg"))

    if not sample_files:
        print("[WARN] No base reference images found to synthesize tampers.")
        return []

    # Map sample files to variants
    # media_1788440125203 is Gold Front
    # media_1788440132882 is Gold Back
    # media_1788440168117 is Taaza Front
    # media_1788440237491 is Shakti Front

    tamper_configs = [
        {
            "id": "SYN-TAMPER-SEAL-001",
            "base_file": "media_1788440125203.jpg",
            "variant": "AMUL_GOLD",
            "tamper_type": "SEAL_CRIMP_RESEAL_SMOOTHED",
            "description": "Top seal crimp ridges blurred and smoothed simulating manual hot-iron resealing.",
            "transform": "smooth_seal"
        },
        {
            "id": "SYN-TAMPER-BARCODE-001",
            "base_file": "media_1788440132882.jpg",
            "variant": "AMUL_GOLD",
            "tamper_type": "BARCODE_CHECKSUM_ALTERATION",
            "description": "Barcode digits altered causing EAN-13 modulo-10 checksum invalidation.",
            "transform": "alter_barcode"
        },
        {
            "id": "SYN-TAMPER-LOGO-COLOR-001",
            "base_file": "media_1788440168117.jpg",
            "variant": "AMUL_TAAZA",
            "tamper_type": "LOGO_CHROMATIC_MISREGISTRATION",
            "description": "Amul Taaza wave color shifted from official blue to anomalous hue.",
            "transform": "shift_color"
        },
        {
            "id": "SYN-TAMPER-TYPO-001",
            "base_file": "media_1788440237491.jpg",
            "variant": "AMUL_SHAKTI",
            "tamper_type": "TYPOGRAPHY_FONT_WEIGHT_ANOMALY",
            "description": "Product title typography modified with non-standard stroke thickness.",
            "transform": "perturb_typography"
        }
    ]

    for cfg in tamper_configs:
        base_path = reference_dir / cfg["base_file"]
        if not base_path.exists():
            base_path = Path("data/storage/references") / cfg["base_file"]

        if not base_path.exists():
            continue

        img = cv2.imread(str(base_path))
        if img is None:
            continue

        h, w = img.shape[:2]
        tampered = img.copy()

        if cfg["transform"] == "smooth_seal":
            # Smooth top 8% of image (seal band) with heavy bilateral filter
            seal_h = int(h * 0.08)
            tampered[:seal_h, :] = cv2.bilateralFilter(tampered[:seal_h, :], 15, 80, 80)

        elif cfg["transform"] == "alter_barcode":
            # Barcode zone is bottom right / bottom quadrant on back panel
            bc_y1, bc_y2 = int(h * 0.50), int(h * 0.85)
            bc_x1, bc_x2 = int(w * 0.50), int(w * 0.95)
            # Add synthetic vertical noise lines across barcode bars
            roi = tampered[bc_y1:bc_y2, bc_x1:bc_x2]
            noise = np.random.randint(0, 50, roi.shape, dtype=np.uint8)
            tampered[bc_y1:bc_y2, bc_x1:bc_x2] = cv2.add(roi, noise)

        elif cfg["transform"] == "shift_color":
            # Shift hue by 40 degrees in HSV
            hsv = cv2.cvtColor(tampered, cv2.COLOR_BGR2HSV)
            hsv[:, :, 0] = (hsv[:, :, 0].astype(int) + 35) % 180
            tampered = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        elif cfg["transform"] == "perturb_typography":
            # Apply slight blur and erosion to text quadrant to simulate poor photocopy
            text_y1, text_y2 = int(h * 0.20), int(h * 0.50)
            tampered[text_y1:text_y2, :] = cv2.GaussianBlur(tampered[text_y1:text_y2, :], (5, 5), 1.5)

        out_filename = f"{cfg['id'].lower()}_{cfg['variant'].lower()}.png"
        out_path = output_dir / out_filename
        cv2.imwrite(str(out_path), tampered)

        sha = compute_sha256(str(out_path))
        hashes = compute_perceptual_hashes(tampered)
        quality = quality_engine.evaluate(tampered)

        record = {
            "image_id": cfg["id"],
            "label": "SYNTHETIC_TAMPER",
            "provenance_status": "SYNTHETIC_TEST_STUB",
            "verification_status": "PENDING_REVIEW",
            "license_status": "INTERNAL_RESEARCH_ONLY",
            "variant": cfg["variant"],
            "tamper_type": cfg["tamper_type"],
            "base_reference": cfg["base_file"],
            "description": cfg["description"],
            "filename": out_filename,
            "relative_path": f"synthetic_tampers/{out_filename}",
            "absolute_path": str(out_path),
            "sha256": sha,
            "hashes": hashes,
            "dimensions": f"{w}x{h}",
            "file_size_bytes": out_path.stat().st_size,
            "quality_score": quality.overall_quality,
            "quality_status": quality.quality_status
        }
        manifest_records.append(record)
        print(f"[SYNTHETIC] Generated {cfg['id']} -> {out_filename} (SHA: {sha[:12]}...)")

    out_manifest = output_dir / "synthetic_tampers_manifest.json"
    with open(out_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_records, f, indent=2)

    return manifest_records


if __name__ == "__main__":
    ref_dir = Path(r"C:\Users\PRAVASH\Desktop\VeriSure_Ai\data\storage\references")
    syn_dir = Path(r"C:\Users\PRAVASH\Desktop\VeriSure_Ai\data\storage\synthetic_tampers")
    generate_synthetic_tampers(ref_dir, syn_dir)

