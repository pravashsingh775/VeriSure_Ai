"""
VeriSure AI - Storage Subsystem Health and Parity Maintenance Tool
CLI script to audit database-to-storage parity, detect/prune unreferenced orphan files,
verify file integrity, and ensure required directory structures.

Usage:
    python backend/scripts/maintain_storage.py --check
    python backend/scripts/maintain_storage.py --prune
    python backend/scripts/maintain_storage.py --ensure-dirs
    python backend/scripts/maintain_storage.py --check --json
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("maintain_storage")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
STORAGE_DIR = DATA_DIR / "storage"

REQUIRED_SUBDIRS = [
    "raw_scans",
    "crops",
    "heatmaps",
    "references",
    "references_v2",
    "synthetic_tampers",
    "negative_samples",
    "reports",
    "artifacts",
    "temp"
]

GITKEEP_SUBDIRS = [
    "raw_scans",
    "crops",
    "heatmaps",
    "reports",
    "artifacts",
    "temp"
]


def ensure_storage_directories() -> Dict[str, bool]:
    """Ensures all required subdirectories and .gitkeep files exist."""
    results = {}
    for sub in REQUIRED_SUBDIRS:
        sub_path = STORAGE_DIR / sub
        sub_path.mkdir(parents=True, exist_ok=True)
        results[sub] = sub_path.exists()

    for sub in GITKEEP_SUBDIRS:
        gitkeep_path = STORAGE_DIR / sub / ".gitkeep"
        if not gitkeep_path.exists():
            gitkeep_path.touch()
            logger.info(f"Created missing .gitkeep: {gitkeep_path.relative_to(REPO_ROOT)}")

    rag_dir = DATA_DIR / "rag_knowledge"
    rag_dir.mkdir(parents=True, exist_ok=True)
    return results


def get_db_connection():
    """Establishes connection to PostgreSQL using environment or standard credentials."""
    db_user = os.getenv("POSTGRES_USER", "verisure_app")
    db_pass = os.getenv("POSTGRES_PASSWORD", "verisure_secure_pass_2026")
    db_host = os.getenv("POSTGRES_HOST", "172.30.74.29")
    db_port = int(os.getenv("POSTGRES_PORT", "5432"))
    db_name = os.getenv("POSTGRES_DB", "verisure_db")

    return psycopg2.connect(
        user=db_user,
        password=db_pass,
        host=db_host,
        port=db_port,
        dbname=db_name
    )


def audit_storage() -> Dict:
    """Runs comprehensive parity audit between PostgreSQL and storage disk."""
    ensure_storage_directories()

    report = {
        "status": "HEALTHY",
        "data_dir": str(DATA_DIR),
        "storage_dir": str(STORAGE_DIR),
        "missing_db_files": [],
        "orphaned_disk_files": {
            "raw_scans": [],
            "crops": [],
            "heatmaps": [],
            "reports": []
        },
        "counts": {
            "db_reference_images": 0,
            "db_scan_images": 0,
            "db_reports": 0,
            "disk_total_images": 0,
            "disk_total_bytes": 0
        }
    }

    # 1. Total disk images and bytes
    total_bytes = 0
    total_images = 0
    img_exts = {".jpg", ".jpeg", ".png", ".webp"}
    for p in STORAGE_DIR.rglob("*"):
        if p.is_file() and p.name != ".gitkeep":
            total_bytes += p.stat().st_size
            if p.suffix.lower() in img_exts:
                total_images += 1

    report["counts"]["disk_total_images"] = total_images
    report["counts"]["disk_total_bytes"] = total_bytes

    # 2. Database records cross-reference
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Reference images
        cur.execute("SELECT id, image_path FROM reference_images;")
        ref_rows = cur.fetchall()
        report["counts"]["db_reference_images"] = len(ref_rows)
        for r in ref_rows:
            p = STORAGE_DIR / r["image_path"]
            if not p.exists():
                report["missing_db_files"].append({
                    "table": "reference_images",
                    "id": r["id"],
                    "expected_path": str(p)
                })

        # Scan images
        cur.execute("SELECT id, image_path, crop_path, heatmap_path FROM scan_images;")
        scan_rows = cur.fetchall()
        report["counts"]["db_scan_images"] = len(scan_rows)

        db_scans = set()
        db_crops = set()
        db_heatmaps = set()

        for s in scan_rows:
            for col, col_set, folder in [
                ("image_path", db_scans, "raw_scans"),
                ("crop_path", db_crops, "crops"),
                ("heatmap_path", db_heatmaps, "heatmaps")
            ]:
                val = s.get(col)
                if val:
                    p = STORAGE_DIR / val
                    col_set.add(p.name)
                    if not p.exists():
                        report["missing_db_files"].append({
                            "table": "scan_images",
                            "id": s["id"],
                            "field": col,
                            "expected_path": str(p)
                        })

        # Reports
        cur.execute("SELECT id, pdf_path FROM reports WHERE pdf_path IS NOT NULL;")
        rep_rows = cur.fetchall()
        report["counts"]["db_reports"] = len(rep_rows)
        db_reports = set()
        for rp in rep_rows:
            val = rp["pdf_path"]
            if val:
                p = STORAGE_DIR / val
                db_reports.add(p.name)
                if not p.exists():
                    report["missing_db_files"].append({
                        "table": "reports",
                        "id": rp["id"],
                        "expected_path": str(p)
                    })

        cur.close()
        conn.close()

        # 3. Disk orphans detection
        disk_scans = set(p.name for p in (STORAGE_DIR / "raw_scans").glob("*") if p.is_file() and p.name != ".gitkeep")
        report["orphaned_disk_files"]["raw_scans"] = sorted(list(disk_scans - db_scans))

        disk_crops = set(p.name for p in (STORAGE_DIR / "crops").glob("*") if p.is_file() and p.name != ".gitkeep")
        report["orphaned_disk_files"]["crops"] = sorted(list(disk_crops - db_crops))

        disk_heatmaps = set(p.name for p in (STORAGE_DIR / "heatmaps").glob("*") if p.is_file() and p.name != ".gitkeep")
        report["orphaned_disk_files"]["heatmaps"] = sorted(list(disk_heatmaps - db_heatmaps))

        disk_reports = set(p.name for p in (STORAGE_DIR / "reports").glob("*.pdf") if p.is_file())
        report["orphaned_disk_files"]["reports"] = sorted(list(disk_reports - db_reports))

    except Exception as e:
        report["status"] = "ERROR"
        report["error"] = str(e)
        logger.error(f"Database connection failed during audit: {e}")
        return report

    total_orphans = sum(len(v) for v in report["orphaned_disk_files"].values())
    if report["missing_db_files"]:
        report["status"] = "DEGRADED_MISSING_FILES"
    elif total_orphans > 0:
        report["status"] = "ORPHANS_DETECTED"
    else:
        report["status"] = "HEALTHY"

    return report


def prune_orphaned_files(report: Dict) -> Dict[str, int]:
    """Safely deletes orphaned files from raw_scans, crops, and heatmaps."""
    pruned_counts = {"raw_scans": 0, "crops": 0, "heatmaps": 0, "reports": 0}

    for category, filenames in report.get("orphaned_disk_files", {}).items():
        folder = STORAGE_DIR / category
        for fn in filenames:
            file_path = folder / fn
            if file_path.exists() and file_path.is_file() and fn != ".gitkeep":
                try:
                    file_path.unlink()
                    pruned_counts[category] += 1
                    logger.info(f"Pruned orphan file: {file_path.relative_to(REPO_ROOT)}")
                except Exception as ex:
                    logger.error(f"Failed to prune {file_path}: {ex}")

    return pruned_counts


def main():
    parser = argparse.ArgumentParser(description="VeriSure AI Storage Maintenance Tool")
    parser.add_argument("--check", action="store_true", help="Perform parity check and audit")
    parser.add_argument("--prune", action="store_true", help="Prune unreferenced orphaned files from storage")
    parser.add_argument("--ensure-dirs", action="store_true", help="Ensure all storage directories and .gitkeeps exist")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if not (args.check or args.prune or args.ensure_dirs):
        parser.print_help()
        sys.exit(0)

    if args.ensure_dirs:
        dirs = ensure_storage_directories()
        logger.info(f"Storage directories verified ({len(dirs)} subdirectories OK)")

    audit = audit_storage()

    if args.prune:
        total_orphans = sum(len(v) for v in audit.get("orphaned_disk_files", {}).values())
        if total_orphans > 0:
            logger.info(f"Pruning {total_orphans} orphaned files...")
            pruned = prune_orphaned_files(audit)
            logger.info(f"Pruning completed: {pruned}")
            # Re-run audit after pruning
            audit = audit_storage()
        else:
            logger.info("No orphaned files found to prune.")

    if args.json:
        print(json.dumps(audit, indent=2))
    else:
        print("\n=======================================================")
        print("          VERISURE AI STORAGE AUDIT REPORT             ")
        print("=======================================================")
        print(f"Overall Status:        {audit['status']}")
        print(f"Total Disk Images:     {audit['counts']['disk_total_images']}")
        size_mb = round(audit['counts']['disk_total_bytes'] / (1024 * 1024), 2)
        print(f"Total Storage Size:    {size_mb} MB")
        print(f"DB Reference Images:   {audit['counts']['db_reference_images']}")
        print(f"DB Scan Images:        {audit['counts']['db_scan_images']}")
        print(f"DB Generated Reports:  {audit['counts']['db_reports']}")
        print(f"Missing DB Files:      {len(audit['missing_db_files'])}")

        orphans = audit["orphaned_disk_files"]
        print(f"Orphaned Raw Scans:    {len(orphans['raw_scans'])}")
        print(f"Orphaned Crops:        {len(orphans['crops'])}")
        print(f"Orphaned Heatmaps:     {len(orphans['heatmaps'])}")
        print(f"Orphaned Reports:      {len(orphans['reports'])}")
        print("=======================================================\n")

    if audit.get("missing_db_files"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
