# VeriSure AI — Operational Scope, Limitations & Disclaimers

> **Core Principle**: A system that claims 100% authenticity from a smartphone photograph is scientifically dishonest. This document outlines the physical and technical boundaries of VeriSure AI.

---

## 1. What VeriSure AI CAN Do

1. **Packaging Conformity Assessment**: Evaluate whether the visual appearance, logo keypoints, layout proportions, CIELAB color distribution, and surface texture match authorized brand reference templates.
2. **Physical Heat-Seal Inspection**: Analyze top and bottom crimp seams for irregularities characteristic of manual ironed resealing, syringe puncture marks, or cut-and-resealed pouches.
3. **Structured Regulatory Extraction**: Parse and validate visible manufacturing dates, expiry dates, batch codes, MRP values, and 14-digit FSSAI license structures.
4. **Machine-Readable Checksum Verification**: Decode EAN-13 barcodes and verify Modulo-10 parity checks against the registered product catalog.
5. **Calibrated Evidential Risk Scoring**: Synthesize multi-engine outputs into an explainable 0–100 Risk Score with localized visual difference heatmaps.

---

## 2. What VeriSure AI CANNOT Do (Physical Limitations)

1. **Chemical & Biological Milk Testing**:
   * **Limitation**: A 2D photograph of an opaque polyethylene pouch **cannot verify the liquid contents inside**.
   * **Disclaimer**: VeriSure cannot detect whether milk has been watered down, contaminated with bacteria, or adulterated with chemical compounds (urea, detergent, starch, formalin). Chemical testing requires lab chromatography or lactometer analysis.
2. **Absolute Barcode Proof**:
   * **Limitation**: An authentic EAN-13 barcode printed on a milk pouch can easily be photocopied or duplicated by counterfeiters.
   * **Disclaimer**: A valid barcode is **supporting evidence**, not absolute proof of genuineness.
3. **Live Government Database Verification**:
   * **Limitation**: Unless an official state/central FSSAI or BIS API key is configured by the deployment administrator, VeriSure performs **syntactic and mathematical structure validation** of 14-digit license codes, not real-time registry queries.
4. **Extreme Lighting & Severe Occlusion**:
   * **Limitation**: If more than 22% of the packaging is obscured by specular glare or the image is out-of-focus ($\sigma^2_{\text{Laplacian}} < 80$), the system cannot reliably compare micro-textures.
   * **Protocol**: Under these conditions, the system outputs `INSUFFICIENT_EVIDENCE` and guides the user to recapture. It will never guess or fabricate scores.

---

## 3. Product Terminology Guidelines

In all user interfaces and public documentation:
* Use: **"Authenticity Risk Assessment"**
* Do NOT use: *"100% Certified Genuine"*, *"Guaranteed Authentic"*, or *"Lab Certified"*.

