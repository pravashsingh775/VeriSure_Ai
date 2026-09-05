# VeriSure AI — Scientific Dataset & Reference Corpus Audit Report

**Date of Audit**: 2026-09-05 05:23:56 UTC  
**Corpus Scope**: Amul Gold, Amul Taaza, Amul Shakti  
**Audit Purpose**: Provenance verification, 12-engine feature extraction audit, data leakage prevention, and ML readiness evaluation.

---

## 1. Executive Corpus Summary

| Dataset Partition | Sample Count | Provenance Tier | Primary Role |
|:---|:---:|:---|:---|
| **Reference Corpus V1 (Baseline)** | 12 | Level 1 (Official Brand Origin) | Fixed ground-truth factory standard (Immutable) |
| **Reference Corpus V2 (Expanded)** | 11 | Level 2 (Open Food Facts / Authorized) | Multi-pack & 360° dual-panel packaging references |
| **Negative & Out-of-Scope Corpus** | 5 | Level 3 (Verified External / Competitor) | Open-set rejection calibration (Mother Dairy, diagrams) |
| **Synthetic Tamper Corpus** | 4 | Controlled Synthesis (Synthetic Stub) | Robustness testing for crimp, barcode, & color anomalies |
| **Total Curated Samples** | **32** | Multi-Tier Trust Hierarchy | Complete multimodal verification dataset |

---

## 2. Product Class & Variant Balance

The reference dataset focuses strictly on the 3 authorized Amul milk variants:

```
Amul Gold (Full Cream Milk):     11 references (47.8%)
Amul Taaza (Toned Milk):          8 references (34.8%)
Amul Shakti (Standardised Milk):  4 references (17.4%)
```

- **Open-Set Negative Samples**: 5 verified out-of-scope samples (Competitor brand: Mother Dairy; Non-product graphics: C4 diagrams).
- **Verified Front/Back Pairs**: 3 matched packaging pairs with compatible dimensions, variant, and version.

---

## 3. View Angle & Packaging Morphology Breakdown

| Packaging View | Count | Percentage |
|:---|:---:|:---:|
| **FRONT (Hero Artwork, Logo, Typography)** | 8 | 34.8% |
| **BACK (Barcode, FSSAI, Nutrition Matrix)** | 9 | 39.1% |
| **DETAIL / MACRO (Seals, Storage, Instructions)** | 6 | 26.1% |

---

## 4. 10-Dimension Image Quality Distribution

All reference images were subjected to the **PackagingQualityEngine10D** evaluating resolution, blur, sharpness, brightness, contrast, saturation, exposure, glare, compression artifacts, and text readability.

- **Mean Overall Quality**: 0.827 / 1.000
- **Standard Deviation**: ±0.092
- **Quality Range**: 0.642 (Minimum) — 0.999 (Maximum)
- **Usability Ratio**: 100.0% of approved references satisfy $\ge 0.45$ quality and $\ge 250$px dimension threshold.

---

## 5. Provenance & Trust Tier Distribution

| Provenance Level | Description | Image Count | Trust Weight |
|:---|:---|:---:|:---:|
| **Level 1** | Official Brand Origin (`amul.com` / GCMMF Documentation) | 12 | 1.00 |
| **Level 2** | Authorized Source (Open Food Facts Public Packaging Archive) | 9 | 0.95 |
| **Level 3** | Verified External (Curated retail captures & negative controls) | 7 | 0.80 |
| **Level 5** | Synthetic Test Stub (Controlled perturbations for robustness) | 4 | 0.00 (Test Only) |

---

## 6. Data Leakage & Deduplication Audit

- **Exact Duplicate Violations**: 0 (Zero duplicate SHA-256 hashes across reference corpus).
- **Perceptual Deduplication**: Evaluated via DCT pHash ($H \le 4$). Duplicate web occurrences were registered under canonical images in `duplicate_sources[]` rather than bloating the dataset.
- **Physical Sample Count vs Image Count**: For web packaging images, `physical_sample_id = UNKNOWN` is explicitly recorded to avoid false claims of distinct physical packaging samples.

---

## 7. Machine Learning Readiness & Next Steps

1. **Open-Set Gatekeeper Calibration**: Negative samples (Mother Dairy, diagrams) successfully verified with 0 false-positive counterfeits.
2. **Feature Database Storage**: All 12 engine feature blocks (`LOGO`, `LAYOUT`, `COLOR_PALETTE`, `TYPOGRAPHY`, `TEXTURE_LBP`, `SHAPE`, `SEAL`, `PRINT`, `OCR`, `BARCODE`, `QR`, `CERTIFICATION`) are indexed in PostgreSQL.
3. **Partition Recommendation**:
   - Train on Canonical Reference Fingerprints + Synthetic Tampers for anomaly boundaries.
   - Evaluate on distinct retail test sessions without cross-sample leakage.
