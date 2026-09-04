# VeriSure AI — Dataset Governance & Reference Corpus Specification

---

## 1. Authoritative V1 Reference Corpus

The **V1 Reference Corpus** is the sole authorized image dataset for the current development release of VeriSure AI.

* **Physical Location**: `data/storage/references/`
* **Total Images**: Exactly 12 original images
* **Product Domain**: Amul Milk
* **Source Provenance**: `OFFICIAL_BRAND_ORIGIN` (collected from [https://amul.com/milk](https://amul.com/milk))
* **Immutability Policy**: Strict read-only. Never resized, re-compressed, renamed, deleted, augmented, or replaced.

---

## 2. Cryptographic Manifest & Image Registry

Tracked authoritatively in `data/reference_corpus_v1_manifest.json`:

| Image ID | Variant | View Type | Physical Filename | Dimensions | SHA-256 Cryptographic Hash |
|---|---|:---:|---|:---:|---|
| `GOLD-REF-001` | Amul Gold | FRONT | `media_1788440125203.jpg` | 500 × 500 | `88c5574b5a78afa831b06022f7de06226278822e4418cbb41be589d738b18f7f` |
| `GOLD-REF-002` | Amul Gold | BACK | `media_1788440132882.jpg` | 500 × 500 | `ea311581f56163e78630aabc87e3129eca0fdca206de0c21debff3e965cf8679` |
| `GOLD-REF-003` | Amul Gold | DETAIL | `media_1788440139783.jpg` | 500 × 500 | `7bd216d59d44660864f2ef9b618b8a09eba356b9f531d70eb864551cd9a7713e` |
| `GOLD-REF-004` | Amul Gold | DETAIL | `media_1788440147040.jpg` | 500 × 500 | `61c16ee54bd282403c177404286378a9a177590383e7eb620c174bd05c706310` |
| `TAZA-REF-001` | Amul Taaza | FRONT | `media_1788440168117.jpg` | 500 × 500 | `cd81235bb8e186d062a334cab6795e51f740b8596ced37dac7de322961887891` |
| `TAZA-REF-002` | Amul Taaza | BACK | `media_1788440175260.jpg` | 500 × 500 | `7d4c002351d0f07f4829b3bbffece98fe2e24614f7ff864109c25cd492484ca1` |
| `TAZA-REF-003` | Amul Taaza | DETAIL | `media_1788440184370.jpg` | 500 × 500 | `310718d68569a90dcd07d632569c86bcb8787f830e4dfbbb830a13c4cffbdc06` |
| `TAZA-REF-004` | Amul Taaza | DETAIL | `media_1788440198814.jpg` | 500 × 500 | `032faf82a91fa526eb4a910450a30fc8e1c89c523790bcdb7cafc3a94db997f9` |
| `SHAKTI-REF-001`| Amul Shakti | FRONT | `media_1788440237491.jpg` | 500 × 500 | `0bfc640bc967e4f28ee21dd807e4706d44bb7266c57692a8d0f6cdc6140bbada` |
| `SHAKTI-REF-002`| Amul Shakti | BACK | `media_1788440250225.jpg` | 500 × 500 | `2951972266effaa3be3cbb80081d065e1fde68aa4695712b2507b0411bf97546` |
| `SHAKTI-REF-003`| Amul Shakti | DETAIL | `media_1788440258275.jpg` | 500 × 500 | `508dd94163b0019baf745cfaa94a8c4007b2d6aa7a7debe286351df96a75d14c` |
| `SHAKTI-REF-004`| Amul Shakti | DETAIL | `media_1788440267324.jpg` | 500 × 500 | `97977e5b14e892eb839a5cb31c2ab6adee35beb54f7f5652c5d337d86dc81992` |

---

## 3. Strict Dataset Terminology Policy

1. **What V1 Is**:
   * Reference establishment
   * Packaging fingerprint baseline creation
   * Deterministic feature extraction
   * Pipeline verification
   * Reference candidate retrieval
2. **What V1 Is NOT**:
   * Do NOT call V1 an "ML training dataset"
   * Do NOT call V1 a "test/validation split"
   * Do NOT call V1 an "empirical accuracy benchmark"
   * Do NOT call V1 a "counterfeit dataset"

---

## 4. Derived Artifacts vs Dataset Boundary

The following subdirectories are **runtime-derived output locations only**:
* `data/storage/crops/`
* `data/storage/heatmaps/`
* `data/storage/raw_scans/`
* `data/storage/reports/`
* `data/storage/artifacts/`

**Architectural Law**: Files generated in these directories during scan processing are ephemeral outputs. They are **never** indexed or registered as reference dataset samples.

---

## 5. Future Empirical Benchmark Dataset (Phase 8+)

A separate, future empirical evaluation dataset will be captured from physical retail packages:
* **Target Size**: 30 unique physical packets (10 Taaza, 10 Gold, 10 Shakti)
* **Captures**: 8 controlled angles and lighting conditions per packet (Front, Back, Tilt, High Light, Low Light, Glare, Distance, Occlusion)
* **Total Samples**: 240 physical photographs
* **Versioning**: Tracked under a distinct dataset version `DATASET-EMPIRICAL-V1` separate from the V1 Reference Corpus.
* **Strict Rule**: Zero synthetic or manufactured samples will be represented as real counterfeit data.

