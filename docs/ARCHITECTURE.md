# VeriSure AI — System Architecture & Technical Specification

> **AI-Based Product Authenticity Risk Assessment & Brand Protection Platform**  
> *Initial Domain: Amul Dairy & Milk Packaging | Architecture: Brand-Agnostic FMCG*

---

## 1. Executive Summary & Philosophy

Counterfeit and tampered FMCG goods represent a severe public health hazard, economic drain, and reputational risk to trusted cooperatives such as Amul. Conventional anti-counterfeit systems suffer from two fatal design flaws:
1. **The Monolithic Black-Box Fallacy**: Attempting to train a single deep neural network on packaging photos produces uninterpretable predictions, hallucinates high confidence on novel counterfeits, and fails to identify physical tampering (e.g. syringe puncture or ironed reseals).
2. **False Claims of Contents Certification**: A 2D photograph of a milk pouch **cannot** verify the biochemical purity of liquid milk inside. Claiming 100% legal authenticity certification from a camera scan is scientifically dishonest.

**VeriSure AI** resolves both flaws by introducing an **Evidence-Verification Architecture**:
- It evaluates packaging across **12 independent, replaceable visual, textual, and machine-readable engines**.
- It treats each engine's output as an **evidence object** with explicit certainty, coverage, and quality scores.
- It detects **cross-engine contradictions** (e.g., logo matches authentic artwork, but barcode is inconsistent or heat-seal crimp indicates manual ironed tampering).
- It generates **calibrated authenticity risk scores (0–100)** with grounded natural language explanations and pixel-wise difference heatmaps.

---

## 2. End-to-End System Pipeline

```mermaid
flowchart TD
    A[Consumer Photograph] --> B[Image Quality Engine]
    B -->|Blur / Glare / Dark| C[Insufficient Evidence Verdict & Recapture Guidance]
    B -->|Pass Quality Gate| D[Product Boundary Detector]
    D --> E[Cropped Packaging Region]
    
    E --> F[Fast OCR & Barcode Reader]
    F --> G[Hierarchical Reference Retriever]
    G --> H[(Packaging Version Registry)]
    H -->|Active Template & Metadata| I[Candidate Reference Template]
    
    E & I --> J1[Logo Keypoint Homography Analyzer]
    E & I --> J2[Layout Spatial Density Analyzer]
    E & I --> J3[CIELAB CIE2000 Colour Analyzer]
    E & I --> J4[Typography Stroke Width Analyzer]
    E & I --> J5[LBP Texture Invariant Analyzer]
    E & I --> J6[Contour Hu Moments Shape Analyzer]
    E & I --> J7[Heat-Seal Crimp Gradient Analyzer]
    E & I --> J8[Print Acuity & Bleed Analyzer]
    E & I --> J9[Structured OCR Field Validator]
    E & I --> J10[EAN-13 Modulo-10 Barcode Verifier]
    E & I --> J11[QR Domain Registry Verifier]
    E & I --> J12[FSSAI 14-Digit Regulatory Engine]
    
    J1 & J2 & J3 & J4 & J5 & J6 & J7 & J8 & J9 & J10 & J11 & J12 --> K[Multi-Evidence Fusion Engine]
    K --> L[Contradiction & Conflict Detector]
    L --> M[Calibrated Decision Engine]
    
    M --> N1[Authenticity Risk Score 0-100]
    M --> N2[Standardized Decision State]
    M --> N3[Difference Heatmap & Anomaly Regions]
    M --> N4[Grounded Explanation Synthesis]
    M --> N5[Packaging Fingerprint Record]
    M --> N6[Publication-Grade Vector PDF Report]
    
    M -->|High Risk / Tampered| O[Automated Suspicious Case Triage]
    O --> P[Human-in-the-Loop Review Queue]
```

---

## 3. The 12 Independent Evidence Engines

### 3.1. Image Quality Engine (`backend/app/ai/quality/engine.py`)
Assesses photographic adequacy before verification:
- **Blur Score**: Variance of Laplacian ($\sigma^2_{\Delta}$). Threshold: $\ge 80.0$.
- **Brightness Score**: Deviations from mid-tone intensity ($\mu = 135$). Detects underexposure ($\mu < 45$) or blowout ($\mu > 235$).
- **Contrast Score**: Standard deviation of pixel intensities ($\sigma_{\text{gray}}$).
- **Specular Glare Ratio**: Identifies desaturated clipped pixels in HSV space ($V > 250, S < 15$). More than 22% flags `HARSH_PACKAGING_GLARE`.
- **Framing / Occlusion**: Border edge activity via Canny filtering to detect severe cutoff.

### 3.2. Packaging Boundary Detector (`backend/app/ai/detection/engine.py`)
- Canny edge detection followed by morphological closing ($15 \times 15$ kernel).
- Finds external contours and filters by packaging area ratio ($> 15\%$) and aspect ratio ($0.45 \le \text{AR} \le 2.2$).
- Crops packaging into normalized ROI.

### 3.3. Logo Keypoint & Homography Analyzer (`backend/app/ai/vision/logo.py`)
- ORB keypoint detector (500 features).
- Lowe's ratio test ($0.75$) with k-Nearest Neighbors (k-NN).
- RANSAC homography estimation; computes inlier consensus ratio.
- Normalized Cross-Correlation (NCC) and HSV color correlation on warped logo patch.

### 3.4. Layout Spatial Density Profiler (`backend/app/ai/vision/layout.py`)
- 4-band spatial density profiling across vertical and horizontal axes.
- Computes relative element displacement and center-of-mass shift.

### 3.5. CIELAB Colour Analyzer (`backend/app/ai/vision/colour.py`)
- Converts BGR image to device-independent CIELAB color space.
- Performs k-means clustering ($k=4$) to extract dominant packaging palette.
- Computes Euclidean and CIE2000 $\Delta E$ color distance against genuine brand palette.

### 3.6. Typography & Stroke Width Analyzer (`backend/app/ai/vision/typography.py`)
- Otsu adaptive binarization to segment print characters.
- Euclidean Distance Transform (EDT) computes continuous stroke width distribution.
- Coefficient of variation ($\text{CV} = \sigma_{\text{stroke}} / \mu_{\text{stroke}}$) detects uneven ink bleed or blurry counterfeit typesetting.

### 3.7. Texture Invariant Analyzer (`backend/app/ai/vision/texture.py`)
- Uniform Local Binary Patterns ($P=8, R=1$).
- Calculates 59-bin normalized LBP histogram.
- Chi-square distance ($\chi^2$) measures micro-texture deviation of packaging substrate.

### 3.8. Packaging Shape & Hu Moments Analyzer (`backend/app/ai/vision/shape.py`)
- Extracts external contour polygon.
- Computes 7 log-transformed Hu Moment invariants for scale, translation, and rotation invariance.

### 3.9. Heat-Seal Crimp Gradient Analyzer (`backend/app/ai/vision/seal.py`)
- Isolates top (0–8%) and bottom (92–100%) sealing zones.
- Applies Sobel Y derivative operator to detect periodic crimping ridges produced by industrial form-fill-seal (FFS) machinery.
- Anomaly detection: Flat, smooth, or melted ridges indicate manual household iron reseals or counterfeit packaging.

### 3.10. Print Acuity & Chromatic Bleed Analyzer (`backend/app/ai/vision/print.py`)
- High-frequency edge gradient magnitude measures industrial flexographic / rotogravure print sharpness.
- Channel cross-correlation between Red and Blue channels measures ink registration fringing.

### 3.11. Code & Structured OCR Engines (`backend/app/ai/ocr/engine.py`, `codes/`)
- **OCR Engine**: Extracts raw text, parses MRP, FSSAI, batch number, manufacturing & expiry dates using contextual regular expressions.
- **Barcode Analyzer**: ZXing-CPP decoder, validates EAN-13 Modulo-10 checksum digit, and checks registered brand catalog barcode.
- **QR Analyzer**: Decodes 2D barcode payload and validates target domain against registered brand URL whitelist.
- **Certification Analyzer**: Validates 14-digit Indian FSSAI license format, extracts registration jurisdiction (e.g. Code 24 Gujarat), and verifies format validity.

---

## 4. Multi-Evidence Fusion & Contradiction Detection

VeriSure AI strictly avoids simple arithmetic averaging. Instead, evidence is synthesized through calibrated weighted fusion:

$$w_i = W_{\text{base}}(e_i.\text{type}) \times e_i.\text{confidence} \times e_i.\text{quality}$$

### Contradiction Penalty Matrix
When independent engines return contradictory high-confidence signals:
1. **Artwork Matches vs Barcode Mismatch**: Logo $> 0.80$ but Barcode $< 0.30$ $\implies$ Penalty $\Delta_1 = 0.20$ ("Possible packaging replica or outdated version").
2. **Artwork Matches vs Seal Compromised**: Logo $> 0.75$ but Seal $< 0.35$ $\implies$ Penalty $\Delta_2 = 0.25$ ("Physical tampering or manual reseal").
3. **OCR Text Valid vs QR Phishing**: OCR $> 0.80$ but QR domain unverified $\implies$ Penalty $\Delta_3 = 0.15$.

$$\Delta_{\text{conflict}} = \min(0.45, \sum \Delta_k)$$

### Fused Authenticity & Risk Score
$$S_{\text{fused}} = \left(\frac{\sum w_i \cdot s_i}{\sum w_i}\right) \times (1.0 - \Delta_{\text{conflict}})$$

$$\text{Risk Score} = \text{round}\Big((1.0 - S_{\text{fused}}) \times 100.0, 1\Big)$$

$$\text{Uncertainty} = 1.0 - \Big(\text{Coverage} \times \text{Mean Quality} \times (1.0 - \Delta_{\text{conflict}})\Big)$$

---

## 5. Decision State Machine

| State | Risk Score | Coverage | Conditions | Advisory Action |
|---|---|---|---|---|
| `INSUFFICIENT_EVIDENCE` | 50.0 | — | Image quality gate failed (blur, glare, dark) | Recapture photograph following guided checklist |
| `UNSUPPORTED_PRODUCT` | 50.0 | — | Packaging not found in active catalog | Product not cataloged in reference database |
| `TAMPERED_OR_DAMAGED` | $\ge 75.0$ | Any | Seal crimp score $< 0.35$ | **DO NOT CONSUME.** Package integrity compromised |
| `CRITICAL_RISK` | $\ge 70.0$ | Any | Multi-marker deviation or severe contradiction | High counterfeit probability. Report to brand |
| `HIGH_RISK` | $45.0 - 69.9$ | Any | Significant deviations from factory standard | Exercise caution. Verify retail purchase receipt |
| `MEDIUM_RISK` | $20.0 - 44.9$ | Any | Noticeable variations; potential batch tolerance | Verify retail source |
| `LOW_RISK` | $10.0 - 19.9$ | $\ge 0.65$ | High conformity with minor tolerance | Low counterfeit risk based on available packaging evidence |
| `LIKELY_GENUINE` | $< 10.0$ | $\ge 0.75$ | High confidence, all markers congruent | Packaging aligns closely with factory reference (cannot verify internal contents) |

---

## 6. Difference Heatmaps & Report Generation

- **SSIM Difference Heatmap**: Normalizes scan crop to reference dimensions, computes structural difference map, applies Gaussian smoothing to suppress sensor noise, and blends a **JET pseudo-color overlay** (Blue = Identical match, Red = Structural difference).
- **Salient Anomaly Detection**: Extracts bounding boxes of difference regions exceeding $2\%$ of package area and computes regional difference magnitudes.
- **Publication-Grade PDF**: ReportLab generates vector PDF reports containing scan metadata, executive verdict, evidence breakdown table, consumer advisory, and mandatory academic disclaimers.

---

## 7. End-to-End Verification Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Consumer
    participant UI as Frontend SPA (React)
    participant API as FastAPI Backend (/api/v1)
    participant Orch as AIPipelineOrchestrator
    participant Quality as QualityEngine
    participant Detect as ProductDetector
    participant Retr as ReferenceRetriever
    participant Engines as 12 Evidence Engines
    participant Fusion as Fusion & Decision Engine
    participant PDF as VeriSurePDFGenerator
    participant DB as Relational Database

    Consumer->>UI: Upload / Capture Product Photo
    UI->>API: POST /scans/upload (multipart/form-data)
    API->>DB: Create ScanRecord (status="UPLOADING")
    API->>Orch: execute_pipeline(image_bgr)
    
    Orch->>Quality: assess(image_bgr)
    alt Quality Insufficient (Blur / Glare / Dark)
        Quality-->>Orch: usable=False, InsufficientEvidence
        Orch->>Fusion: evaluate_fallback(usable=False)
        Fusion-->>Orch: Decision(state="INSUFFICIENT_EVIDENCE")
        Orch-->>API: Return Recapture Guidance
        API-->>UI: Display Recapture Checklist (No fake scores)
    else Quality Sufficient
        Quality-->>Orch: usable=True
        Orch->>Detect: detect(image_bgr)
        Detect-->>Orch: Normalized Product Crop
        Orch->>Retr: retrieve_candidates(detected_text, barcode)
        Retr->>DB: Query packaging_versions & reference_fingerprints
        DB-->>Retr: Matched Active Reference Template
        Retr-->>Orch: Best Candidate Packaging Version
        
        par Parallel Evidence Analysis
            Orch->>Engines: Visual: Logo, Layout, Colour, Texture, Shape, Print, Seal
            Orch->>Engines: Text & Codes: OCR Fields, Barcode, QR, FSSAI
        end
        Engines-->>Orch: 12 Standardized EvidenceObjects
        
        Orch->>Fusion: fuse(evidences, quality_result)
        Fusion-->>Orch: AuthenticityScore, Contradictions, RiskScore, DecisionState
        
        Orch->>PDF: generate_report(decision, evidences, metadata)
        PDF-->>Orch: Vector PDF Saved (with SHA-256)
        
        Orch-->>API: Pipeline Output Dictionary
        API->>DB: Persist Evidences, Decision, Fingerprint, ReportRecord
        API-->>UI: 201 Created (Full ScanDetail JSON)
        UI-->>Consumer: Render Risk Gauge, Narrative, Heatmap, PDF Download
    end
```

---

## 8. Physical Deployment Architecture

```mermaid
flowchart TD
    subgraph Client_Tier [Client Tier]
        C1[Mobile Smartphone Browser]
        C2[Desktop / Tablet Browser]
    end

    subgraph Presentation_Tier [Presentation & Web Gateway]
        Vite[Vite + React SPA Server / Nginx]
        CORS[CORS Policy Guard]
    end

    subgraph Application_Tier [FastAPI Application Tier]
        Uvicorn[Uvicorn ASGI Engine :8000]
        Router[API v1 Routers]
        AuthGuard[JWT / RBAC Dependency Guard]
        Orchestrator[AIPipelineOrchestrator]
        VisionLib[OpenCV / NumPy / SciPy CV Pipeline]
        OCRLib[PaddleOCR / Tesseract Engine]
        ReportLib[ReportLab PDF Engine]
    end

    subgraph Persistence_Tier [Data & Storage Tier]
        DB[(PostgreSQL 16 / SQLite dev)]
        Storage[(Local Storage: data/storage/)]
        RefDir[references/ - 12 V1 Authoritative Images]
        DerivedDir[crops/ heatmaps/ reports/ artifacts/]
    end

    C1 & C2 -->|HTTPS / WSS| Vite
    Vite -->|Proxy /api/v1| CORS
    CORS --> Uvicorn
    Uvicorn --> Router
    Router --> AuthGuard
    AuthGuard --> Orchestrator
    Orchestrator --> VisionLib & OCRLib & ReportLib
    Router & Orchestrator -->|Async SQLAlchemy 2.0| DB
    Orchestrator & ReportLib -->|Storage Abstraction| Storage
    Storage --> RefDir & DerivedDir
```

---

## 9. Complete Relational Database ER Diagram

```mermaid
erDiagram
    BRANDS ||--o{ BRAND_USERS : employs
    BRANDS ||--o{ PRODUCTS : owns
    BRANDS ||--o{ BRAND_SETTINGS : configures
    BRANDS ||--o{ SUSPICIOUS_CASES : triages
    USERS ||--o{ BRAND_USERS : member_of
    USERS ||--o{ USER_ROLES : assigned
    ROLES ||--o{ USER_ROLES : defines
    ROLES ||--o{ ROLE_PERMISSIONS : grants
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : specifies

    PRODUCTS ||--o{ PRODUCT_VARIANTS : contains
    PRODUCT_VARIANTS ||--o{ PRODUCT_PACK_SIZES : offers
    PRODUCT_PACK_SIZES ||--o{ PACKAGING_VERSIONS : versions

    PACKAGING_VERSIONS ||--o{ REFERENCE_IMAGES : references
    PACKAGING_VERSIONS ||--o{ REFERENCE_FINGERPRINTS : fingerprints
    REFERENCE_IMAGES ||--o{ REFERENCE_FEATURES : extracts

    USERS ||--o{ SCANS : uploads
    SCANS ||--o{ SCAN_IMAGES : captures
    SCANS ||--o{ EVIDENCES : evaluates
    SCANS ||--o{ DECISIONS : concludes
    SCANS ||--o{ REPORTS : generates
    SCANS ||--o{ SUSPICIOUS_CASES : triggers

    SUSPICIOUS_CASES ||--o{ CASE_REVIEWS : reviews
    FEEDBACK_SAMPLES ||--o{ DATASET_SAMPLES : curates
    DATASETS ||--o{ DATASET_VERSIONS : releases
    DATASET_VERSIONS ||--o{ DATASET_SAMPLES : includes

    ML_MODELS ||--o{ ML_MODEL_VERSIONS : tracks
    ML_MODEL_VERSIONS ||--o{ ML_TRAINING_RUNS : trains
    ML_MODEL_VERSIONS ||--o{ ML_EVALUATION_RUNS : evaluates
    ML_MODEL_VERSIONS ||--o{ ML_MODEL_DEPLOYMENTS : deploys

    BRANDS {
        string id PK
        string name
        string code UK
        string description
        boolean is_active
        datetime created_at
    }

    BRAND_USERS {
        string id PK
        string brand_id FK
        string user_id FK
        string role
        datetime created_at
    }

    USERS {
        string id PK
        string email UK
        string hashed_password
        string full_name
        boolean is_active
        boolean is_superuser
        datetime created_at
    }

    PRODUCTS {
        string id PK
        string brand_id FK
        string name
        string category
        boolean is_active
        datetime created_at
    }

    PRODUCT_PACK_SIZES {
        string id PK
        string variant_id FK
        string pack_size
        string pack_type
        string net_quantity
        datetime created_at
    }

    PACKAGING_VERSIONS {
        string id PK
        string pack_size_id FK
        string version_code
        float expected_mrp
        string expected_barcode
        string status
        datetime created_at
    }

    REFERENCE_IMAGES {
        string id PK
        string packaging_version_id FK
        string view_type
        string image_path
        string original_filename
        string source_type
        string source_document
        string verification_status
        string approval_status
        datetime created_at
    }

    SCANS {
        string id PK
        string user_id FK
        string status
        boolean is_multi_angle
        datetime created_at
    }

    EVIDENCES {
        string id PK
        string scan_id FK
        string evidence_type
        float score
        float confidence
        float reliability
        boolean is_available
        json features
        string explanation
        datetime created_at
    }

    DECISIONS {
        string id PK
        string scan_id FK
        string state
        float risk_score
        float confidence
        float uncertainty
        float evidence_coverage
        string recommendation
        string explanation_summary
        datetime created_at
    }

    REPORTS {
        string id PK
        string scan_id FK
        string pdf_path
        string pdf_sha256
        int file_size_bytes
        datetime generated_at
    }

    FEEDBACK_SAMPLES {
        string id PK
        string scan_id FK
        string case_id FK
        string origin_type
        string verified_label
        string notes
        datetime created_at
    }
```

