# VeriSure AI — Production Data Infrastructure & Storage Architecture

## 1. Overview
The `data/` directory serves as the centralized storage, reference corpus repository, and knowledge base for the **VeriSure AI** packaging verification platform.

It adheres to strict scientific standards:
- **Zero Fabrication**: No synthetic images are presented as authentic packaging.
- **Corpus Immutability**: Baseline reference images (`Reference Corpus V1`) are permanently sealed and protected from modifications.
- **Data-to-Database Parity**: Dynamic uploads in storage are synchronized with PostgreSQL (`verisure_db`).
- **Contextual Knowledge Separation**: Structured textual RAG knowledge provides regulatory context and **never** overrides measured computer vision / ML evidence.

---

## 2. Directory Topology

```
data/
├── dataset_audit_report.md             # Automated audit report for Reference Corpus V2
├── reference_corpus_v1_manifest.json   # Cryptographic manifest for Reference Corpus V1 (12 images)
├── reference_corpus_v2_manifest.json   # Versioned manifest for Reference Corpus V2 (v2.0.0)
├── README.md                           # This infrastructure documentation
│
├── rag_knowledge/                      # Textual RAG Domain Specifications
│   ├── amul_gold_specification.json
│   ├── amul_shakti_specification.json
│   ├── amul_taaza_specification.json
│   └── fssai_packaging_regulations.json
│
└── storage/                            # Physical Blob & Asset Storage Subsystem
    ├── references/                     # Reference Corpus V1 (Factory baseline, 12 images)
    ├── references_v2/                  # Reference Corpus V2 (Authorized Open Food Facts, 21 images)
    ├── synthetic_tampers/              # Controlled synthetic tamper test stubs (4 images + manifest)
    ├── negative_samples/               # Negative evaluation benchmark (Mother Dairy, diagrams)
    ├── raw_scans/                      # Dynamic user-uploaded packaging images (.gitkeep preserved)
    ├── crops/                          # Bounding box crops generated during analysis (.gitkeep preserved)
    ├── heatmaps/                       # Verification difference heatmaps (.gitkeep preserved)
    ├── reports/                        # Generated PDF verification certificates (.gitkeep preserved)
    ├── artifacts/                      # Ephemeral ML models and evaluation dumps (.gitkeep preserved)
    └── temp/                           # Temporary staging area (.gitkeep preserved)
```

---

## 3. Storage Folders & Retention Policy

| Directory | Type | Git Tracked? | Lifecycle & Retention Policy |
| :--- | :--- | :--- | :--- |
| `references/` | Immutable Ground Truth | **Yes** | Permanently retained. Reference Corpus V1 factory baseline. |
| `references_v2/` | Immutable Versioned Dataset | **Yes** | Version `v2.0.0`. Provenance-tracked authorized packaging photographs. |
| `synthetic_tampers/` | Controlled Benchmark Stubs | **Yes** | Controlled perturbations for tamper detection validation (`SYNTHETIC_TEST_STUB`). |
| `negative_samples/` | Evaluation Benchmark | **Yes** | Out-of-scope packaging (`OTHER_BRAND`) and architectural diagrams (`NON_PRODUCT_IMAGE`). |
| `raw_scans/` | Dynamic User Input | **No** (only `.gitkeep`) | Retained as long as scan record exists in `scans` table. Pruned if unreferenced. |
| `crops/` | Derived Asset | **No** (only `.gitkeep`) | Lifecycle tied to parent `ScanImage`. Pruned if unreferenced. |
| `heatmaps/` | Derived Asset | **No** (only `.gitkeep`) | Visual overlays for front/back difference maps. Pruned if unreferenced. |
| `reports/` | Generated Certificate | **No** (only `.gitkeep`) | PDF reports for consumer/brand export. Pruned if unreferenced. |
| `artifacts/` | Staging / Model Cache | **No** (only `.gitkeep`) | Ephemeral cache for ML checkpoint evaluation. |
| `temp/` | Scratch Space | **No** (only `.gitkeep`) | Temporary scratch files during pipeline processing. Cleaned up immediately. |

---

## 4. Reference Corpora & Manifests

### Reference Corpus V1
- **File**: `data/reference_corpus_v1_manifest.json`
- **Scope**: 12 verified factory baseline reference images for Amul Gold, Amul Taaza, and Amul Shakti.
- **Hash Algorithm**: SHA-256 integrity verification.

### Reference Corpus V2 (`v2.0.0`)
- **File**: `data/reference_corpus_v2_manifest.json`
- **Scope**: 11 approved high-resolution packaging reference images, 7 deduplicated occurrences, and 3 verified Front/Back physical sample pairs.
- **Quality Standard**: Evaluated across 10 packaging imaging dimensions with an average score of `0.827` (0 rejects).
- **Provenance**: Level 2 Open Food Facts public archive under CC-BY-SA 3.0 license.

---

## 5. Storage Maintenance & Parity Verification

VeriSure AI includes an automated storage maintenance tool: [`backend/scripts/maintain_storage.py`](file:///c:/Users/PRAVASH/Desktop/VeriSure_Ai/backend/scripts/maintain_storage.py).

### CLI Commands

```bash
# 1. Run read-only database-to-storage parity audit
python backend/scripts/maintain_storage.py --check

# 2. Output audit report in JSON for CI/CD or health endpoints
python backend/scripts/maintain_storage.py --check --json

# 3. Safely prune unreferenced orphaned files from disk
python backend/scripts/maintain_storage.py --prune

# 4. Ensure all required storage subdirectories and .gitkeep files exist
python backend/scripts/maintain_storage.py --ensure-dirs
```

---

## 6. Git & Deployment Rules
1. Never commit raw user scans or dynamic reports (`data/storage/raw_scans/*`, `data/storage/reports/*`).
2. Always keep `.gitkeep` files committed in empty directories to guarantee proper runtime directory structure upon cloning or container deployment.
3. In Docker or Linux environments, ensure the `data/storage/` directory has write permissions for the application user (`chmod -R 775 data/storage`).
