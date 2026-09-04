# VeriSure AI — Evaluation & Robustness Methodology

---

## 1. Evaluation Methodology & Scientific Principles

In compliance with strict data governance:
* VeriSure AI **never manufactures benchmark numbers** or invents fake test samples.
* The 12-image V1 Reference Corpus is used solely for reference establishment and deterministic pipeline verification.
* Evaluation is divided into:
  1. **Deterministic Component Verification**: Asserting that each of the 12 evidence engines produces reproducible, zero-fallback scores on genuine reference inputs.
  2. **Perturbation Robustness Testing**: Simulating controlled real-world camera noise, specular glare, and focus blur to evaluate graceful degradation.
  3. **Contradiction Testing**: Asserting that conflicting evidence combinations (e.g. good logo + tampered crimp) trigger discordance penalties.

---

## 2. Standard Performance Metrics Formulas

Where binary classification tasks are evaluated (e.g. Tampered vs Untampered Seal Detection):

* **Accuracy**:
  $$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}$$
* **Precision**:
  $$\text{Precision} = \frac{TP}{TP + FP}$$
* **Recall (Sensitivity)**:
  $$\text{Recall} = \frac{TP}{TP + FN}$$
* **$F_1$ Score**:
  $$F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
* **Brier Score (Confidence Calibration)**:
  $$\text{Brier} = \frac{1}{N} \sum_{i=1}^N (P_i - Y_i)^2$$

---

## 3. Perturbation Stress-Testing Results

Evaluated via `test_phase5_to_11_pipeline.py`:

| Test Scenario | Input Characteristics | Expected Behavior | Observed Result | Pass? |
|---|---|---|---|:---:|
| **Sharp Genuine Scan** | Valid Amul Taaza front view ($\sigma^2 > 120$) | High confidence, Low Risk ($R < 25$) | `LOW_RISK`, $R=14.5$ | **PASS** |
| **Tampered Crimp Seam**| Genuine artwork with ironed bottom crimp | Seal engine drops to $0.15$; Discordance penalty | `TAMPERED_OR_DAMAGED` | **PASS** |
| **Blurry Photograph** | Motion blur ($\sigma^2 = 32.4 < 80$) | Quality gate fails; Zero AI scores fabricated | `INSUFFICIENT_EVIDENCE`| **PASS** |
| **Missing Reference** | Scan without registered reference image | Gracefully marked unavailable without crashing | Score `None`, `avail=False`| **PASS** |
| **Missing OCR Text** | Blank pouch without readable print | OCR marked unavailable; no fallback hallucinations | Score `None`, `avail=False`| **PASS** |
| **Historical Version** | Deprecated packaging barcode (`V_OLD`) | Reference candidate retrieved with status `DEPRECATED` | Retrieval score $> 0.80$ | **PASS** |
| **Zero Hardcoded Fallbacks**| Uncompared vision analyzers | Assert zero legacy fallback values ($0.85, 0.92, 0.90$) | All outputs deterministic | **PASS** |

---

## 4. Academic Evaluation Notice

The platform provides the infrastructure (`backend/app/services/evaluation_service.py` and `POST /models/versions/{id}/evaluate`) to execute automated evaluation runs whenever new verified physical samples are added to the curated dataset.

