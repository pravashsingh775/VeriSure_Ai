# VeriSure AI — Model Card & Algorithmic Telemetry

---

## 1. Model & Engine Details

* **Platform**: VeriSure AI (Minor Project Edition 2026)
* **Architecture**: Hybrid Deterministic Vision + Multi-Evidence Fusion Architecture
* **Primary Engines**:
  1. `ImageQualityEngine-v1` (Laplacian, HSV Glare, Canny Cutoff)
  2. `ProductDetector-v1` (Adaptive Thresholding, Contour Geometry, Perspective Rectification)
  3. `LogoAnalyzer-v1` (ORB 500 Keypoints, Lowe's Ratio Test, RANSAC Homography)
  4. `LayoutAnalyzer-v1` (4-Band Spatial Density Profiling)
  5. `ColourAnalyzer-v1` (CIELAB Space, $k$-means $k=4$, CIE2000 $\Delta E$)
  6. `TypographyAnalyzer-v1` (Otsu Binarization, Euclidean Distance Transform Stroke Width Variance)
  7. `TextureAnalyzer-v1` (59-Bin Uniform Local Binary Patterns, $\chi^2$ Distance)
  8. `ShapeAnalyzer-v1` (Aspect Ratio, Pouch Contour Hull, Hu Moments)
  9. `SealTamperAnalyzer-v1` (Sobel Y Heat-Crimp Periodic Ridge Frequency)
  10. `PrintQualityAnalyzer-v1` (Frequency Domain Edge Clarity, Chromatic Fringing)
  11. `OCREngine-v1` (PaddleOCR / Tesseract Text & Structured Regex Parser)
  12. `BarcodeAnalyzer-v1` (ZXing EAN-13 Modulo-10 Checksum Verifier)
  13. `QRAnalyzer-v1` (OpenCV QR Detector & Domain Whitelist Validator)
  14. `CertificationAnalyzer-v1` (14-Digit FSSAI License Syntax Validator)
  15. `MultiEvidenceFusionEngine-v1` (Reliability-Weighted Evidential Fusion with Discordance Penalties)

---

## 2. Intended Use & Target Domain

* **Primary Application**: Photographic authenticity risk assessment of FMCG milk pouches.
* **Initial Catalog Scope**: Amul Gold, Amul Taaza, Amul Shakti.
* **Intended Users**:
  * Retail consumers checking packaging integrity prior to purchase/consumption.
  * Brand quality officers triaging suspicious reports and counterfeit alerts.
  * Platform administrators monitoring packaging version compliance.

---

## 3. Factors & Operating Environmental Domain

* **Supported Form Factors**: Flexible polyethylene pouches (500 mL, 1 L).
* **Lighting Conditions**: Diffuse ambient indoor/outdoor light ($45 \le \mu_{\text{gray}} \le 235$).
* **Image Resolution**: Minimum $640 \times 480$ px; recommended $1080 \times 1080$ px.
* **Camera Angle**: Pouch facing perpendicular ($\pm 25^\circ$ tilt tolerance).

---

## 4. Performance & Robustness Profile

The engines were evaluated across standard perturbation benchmarks:

| Environmental Factor | Degraded Condition | Engine Behavior | Output Risk State |
|---|---|---|:---:|
| **Motion / Focus Blur** | $\sigma^2_{\text{Laplacian}} < 80$ | Quality gate fails immediately | `INSUFFICIENT_EVIDENCE` |
| **Specular Glare** | Saturated glare $> 22\%$ | Surface visual score confidence discounted | High Uncertainty |
| **Low Light** | Underexposure ($\mu < 45$) | Quality gate fails; user guided to recapture | `INSUFFICIENT_EVIDENCE` |
| **Pouch Resealing** | Crimpless smooth bottom seam | Seal engine detects missing crimp ridges | `TAMPERED_OR_DAMAGED` |
| **Photocopied Packaging**| EAN-13 barcode valid, but LBP texture mismatch | Discordance penalty triggered | `HIGH_RISK` |
| **Unregistered Product** | Detected text matches no Amul variant | Reference retriever yields 0 candidates | `UNSUPPORTED_PRODUCT` |

---

## 5. Ethical & Scientific Limitations

1. **No Chemical Certification**: A photograph cannot determine whether milk has been diluted with water, adulterated with urea/detergent, or spoiled.
2. **Barcode Limitations**: Barcodes are public information and can be photocopied. Barcode validity is supporting evidence only.
3. **No 100% Guarantee**: Output represents a calibrated risk assessment, not legal certification.

