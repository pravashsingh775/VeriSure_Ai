# VeriSure AI — Multi-Evidence AI Pipeline Specification

> **Architectural Law**: VeriSure is NOT a single black-box AI model. It is a multi-evidence verification system coordinating 12 independent, replaceable visual, textual, and machine-readable engines.

---

## 1. Pipeline Execution Flow

```
[Consumer Photograph]
        │
        ▼
[Stage 1: Image Quality Engine]
        │
   (Pass Gate)
        │
        ▼
[Stage 2: Product Boundary Detector]
        │
  (Crop & Normalize)
        │
        ▼
[Stage 3: Quick OCR & Barcode Reader]
        │
        ▼
[Stage 4: Hierarchical Candidate Reference Retriever]
        │
  (Load Golden Template & Version Specs)
        │
        ▼
[Stage 5: Parallel Evidence Evaluation (12 Independent Engines)]
  ├── LogoAnalyzer (ORB Keypoints + RANSAC Homography)
  ├── LayoutAnalyzer (4-Band Spatial Density Profiling)
  ├── ColourAnalyzer (CIELAB CIE2000 ΔE Distance)
  ├── TypographyAnalyzer (Stroke Width Variance via EDT)
  ├── TextureAnalyzer (59-Bin Uniform Local Binary Patterns)
  ├── ShapeAnalyzer (Contour Aspect Ratio & Hu Moments)
  ├── SealAnalyzer (Crimp Ridge Frequency via Sobel Y)
  ├── PrintQualityAnalyzer (High-Frequency Edge Clarity)
  ├── OCREngine (Regex Field Extraction: MRP, Dates, Batch)
  ├── BarcodeAnalyzer (EAN-13 Modulo-10 Checksum)
  ├── QRAnalyzer (Domain Whitelist Verification)
  └── CertificationAnalyzer (14-Digit FSSAI Validation)
        │
        ▼
[Stage 6: Difference Heatmap & Suspicious Regions]
        │
        ▼
[Stage 7: Multi-Evidence Fusion (Dempster-Shafer / Evidential Combination)]
        │
        ▼
[Stage 8: Decision Engine (Calibrated 0-100 Risk Score)]
        │
        ▼
[Stage 9: Grounded Narrative Explanation & Recommendation]
        │
        ▼
[Stage 10: Multi-Modal Packaging Fingerprint & PDF Report]
```

---

## 2. Mathematical Formulations of the 12 Engines

### 2.1. Image Quality Engine
* **Blur (Laplacian Variance)**:
  $$\sigma^2 = \frac{1}{N} \sum_{x,y} (\nabla^2 I(x,y) - \bar{\nabla^2 I})^2$$
  Threshold: $\sigma^2 \ge 80.0$. Below this, the image is marked `BLURRY` and verification stops to prevent false predictions.
* **Specular Glare**: Ratio of saturated, low-chroma pixels in HSV space ($V > 250, S < 15$).

### 2.2. Logo Keypoint & Homography Analyzer
* Detects 500 ORB keypoints on test crop and reference template.
* Evaluates putative matches via Lowe's ratio test ($0.75$).
* Estimates perspective transformation matrix $H$ via RANSAC.
* Inlier consensus ratio determines geometric authenticity score:
  $$S_{\text{logo}} = \frac{N_{\text{inliers}}}{N_{\text{total\_matches}}}$$

### 2.3. Colour Palette Analyzer (CIELAB Space)
* Converts packaging image to CIE $L^*a^*b^*$ space.
* Performs $k$-means clustering ($k=4$) to extract dominant color centers.
* Calculates CIE2000 color difference $\Delta E_{00}$ between test centers and authorized reference centers:
  $$S_{\text{colour}} = \exp\left(-\frac{\Delta E_{00}}{15.0}\right)$$

### 2.4. Texture Analyzer (Local Binary Patterns)
* Computes rotation-invariant uniform Local Binary Patterns ($P=8, R=1$).
* Employs $\chi^2$ distance between 59-bin LBP histograms:
  $$D_{\chi^2}(H_{\text{test}}, H_{\text{ref}}) = \frac{1}{2} \sum_{i=1}^{59} \frac{(H_{\text{test}}[i] - H_{\text{ref}}[i])^2}{H_{\text{test}}[i] + H_{\text{ref}}[i] + \epsilon}$$
  $$S_{\text{texture}} = 1.0 - \min(1.0, D_{\chi^2} / 0.5)$$

### 2.5. Seal / Tamper Analyzer
* Computes horizontal Sobel gradient $G_y = \frac{\partial I}{\partial y}$ across top and bottom pouch seal zones.
* Industrial heat-crimp machines produce periodic ridges ($f_{\text{crimp}} \approx 1.2 \text{ mm}$ periodicity).
* Absence of crimp peaks or non-uniform smoothed regions indicate manual ironed resealing.

### 2.6. Barcode & QR Engines
* Decodes EAN-13 barcodes using ZXing/OpenCV.
* Validates Modulo-10 checksum:
  $$\left(\sum_{i=1}^{12} d_i \cdot (1 \text{ if } i \text{ odd else } 3)\right) \pmod{10}$$
* Important: Matching barcode is **supporting evidence**, not proof of authenticity.

### 2.7. Certification Engine (FSSAI)
* Syntactically verifies 14-digit FSSAI license structure:
  * Digit 1: Registration (1 = manufacturing)
  * Digits 2-3: State code (e.g. 00 = central license, 24 = Gujarat)
  * Digits 4-5: Year of authorization
  * Digits 6-8: Quantity / category code
  * Digits 9-14: Sequential manufacturing license ID.

---

## 3. Multi-Evidence Fusion & Contradiction Penalty

The fusion engine does NOT average scores blindly. It computes reliability-weighted evidence accumulation with a **Discordance Penalty**:

1. **Evidence Reliability Weight**:
   $$w_i = \text{Confidence}_i \times \text{Quality}_i \times \text{CategoryWeight}_i$$
2. **Discordance Detection**:
   If visual markers match genuine reference ($S_{\text{visual}} > 0.85$) BUT barcode is unregistered or heat-seal is tampered ($S_{\text{tamper}} < 0.30$), the system triggers an evidential contradiction penalty:
   $$\text{Penalty} = 0.35 \times |S_{\text{visual}} - S_{\text{tamper}}|$$
   This elevates the Risk Score and forces the decision state to `TAMPERED_OR_DAMAGED` or `HIGH_RISK`.

---

## 4. Standardized Decision States

| Decision State | Risk Score Range | Interpretation |
|---|:---:|---|
| `LIKELY_GENUINE` | $0.0 \le R \le 20.0$ | All visible markers conform to authorized reference. |
| `LOW_RISK` | $20.0 < R \le 40.0$ | Minor surface wear or slight illumination variance. |
| `MEDIUM_RISK` | $40.0 < R \le 60.0$ | Discrepancies in minor textual or layout markers. |
| `HIGH_RISK` | $60.0 < R \le 80.0$ | Significant packaging deviation or mismatched barcode. |
| `CRITICAL_RISK` | $80.0 < R \le 100.0$ | Counterfeit markers detected across multiple engines. |
| `TAMPERED_OR_DAMAGED` | $50.0 \le R \le 100.0$ | Evidence of compromised heat-seal or puncture. |
| `INSUFFICIENT_EVIDENCE`| N/A | Image too blurry, dark, or occluded to evaluate safely. |
| `UNSUPPORTED_PRODUCT` | N/A | Product not found in authorized brand catalog. |

