# VeriSure AI 🛡️
### AI-Assisted Product Authenticity Risk Assessment & Brand Protection Platform
*Target Domain: Flexible Dairy Packaging (Amul Milk Pouches) | Architecture: Production-Ready, Brand-Agnostic FMCG*

[![CI / Automated Tests](https://img.shields.io/badge/Tests-42%2B%20Passed-success.svg?style=for-the-badge&logo=pytest)](https://github.com/pravashsingh775/VeriSure_Ai)
[![CI](https://github.com/pravashsingh775/VeriSure_Ai/actions/workflows/ci.yml/badge.svg)](https://github.com/pravashsingh775/VeriSure_Ai/actions/workflows/ci.yml)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2018.6-336791.svg?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20Async-009688.svg?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/Frontend-React%2019%20%2B%20TypeScript-61DAFB.svg?style=for-the-badge&logo=react)](https://react.dev/)
[![OpenCV](https://img.shields.io/badge/Computer%20Vision-OpenCV%20%26%20PyTorch-5C3EE8.svg?style=for-the-badge&logo=opencv)](https://opencv.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

---

## 🌟 Executive Summary

**VeriSure AI** is an enterprise-grade, evidence-based anti-counterfeiting and authenticity verification platform engineered specifically for flexible packaging. While traditional anti-counterfeiting solutions rely on fragile 2D QR codes (which can be easily photocopied) or opaque "black-box" neural networks, VeriSure AI evaluates packaging physical integrity across **12 independent computer vision, textual, and machine-readable evidence engines**.

The platform synthesizes these multi-modal signals into a mathematically calibrated **Authenticity Risk Score (0–100)** with pixel-wise difference heatmaps, structured reason codes, and instant tamper-evident PDF inspection certificates.

### 💡 Key Technical Highlights
- 🧠 **Zero-Cost Edge Architecture**: Runs entirely locally on CPU/GPU using OpenCV, PyTorch, and Tesseract OCR without recurring external API fees.
- 🏢 **Multi-Tenant Portals**: Dedicated portals for **Consumers** (real-time scanner), **Brand Managers** (Reference Corpus V1 gallery & telemetry), and **Platform Admins** (human-in-the-loop triage & model registry).
- 🗄️ **Enterprise PostgreSQL Backend**: Dual async/sync connection pools (`asyncpg` for high concurrency + `psycopg2` for Alembic migrations), strict RBAC, and immutable cryptographic audit logging.
- 🎯 **Reference Corpus V1**: 12 official ground-truth reference standards across Amul Gold (Full Cream), Amul Taaza (Toned), and Amul Shakti (Standardised) with SHA-256 cryptographic binding.
- 🧪 **100% Test Coverage**: Full pytest suite with 36/36 automated integration and counterfeit regression tests passing.

---

## 🏗️ System Architecture

```mermaid
graph TD
    A[Client App / Mobile View] -->|HTTP / Multipart Form| B[FastAPI Gateway :8000]
    B --> C[Security & Storage Barrier]
    C --> D[Image Quality Assessment Gate]

    subgraph AI & Computer Vision Pipeline
        D -->|Pass| E[Pouch Detection & ROI Extractor]
        E --> F1[1. Logo ORB + RANSAC Homography]
        E --> F2[2. CIELAB ΔE Color Clustering]
        E --> F3[3. LBP Texture Invariant]
        E --> F4[4. Typography EDT Stroke Acuity]
        E --> F5[5. Sobel Y Heat-Seal Crimp Gradient]
        E --> F6[6. Print Edge Bleed & Chromatic Fringing]
        E --> F7[7. Tesseract Structured OCR Engine]
        E --> F8[8. EAN-13 Barcode Modulo-10 Checksum]
        E --> F9[9. QR Domain Whitelist Validator]
        E --> F10[10. FSSAI 14-Digit Regulatory Engine]
    end

    subgraph Evidence Fusion & Calibration
        F1 & F2 & F3 & F4 & F5 & F6 & F7 & F8 & F9 & F10 --> G[Multi-Evidence Fusion Engine]
        G --> H[Contradiction Penalty Matrix]
        H --> I[Bayesian Calibrator & Decision Synthesizer]
    end

    I --> J1[Pixel-wise SSIM Difference Heatmap]
    I --> J2[Publication-Grade PDF Certificate]
    I --> J3[PostgreSQL 18.6 Database]
    I --> J4[Admin Suspicious Case Triage Queue]
```

---

## 🔬 The 12-Engine Evidence Verification Pipeline

| # | Engine / Module | Technology / Formula | Detection Objective |
|:---:|:---|:---|:---|
| **1** | **Image Quality Gate** | $\text{Var}(\nabla^2 I)$ + HSV Glare Thresholding | Prevents blurry or poorly lit photos from generating false verdicts. |
| **2** | **Packaging Detection** | Otsu Thresholding + Convex Hull Contour Analysis | Isolates pouch boundaries and extracts perspective-corrected ROI. |
| **3** | **Logo Keypoint Matching** | ORB (Oriented FAST and Rotated BRIEF) + RANSAC Homography | Verifies brand insignia geometric consistency and identifies counterfeit copies. |
| **4** | **CIELAB Color Match** | $k$-Means Clustering ($k=4$) + CIE2000 $\Delta E$ Formula | Detects printer ink formulation discrepancies and unauthorized color shifts. |
| **5** | **Typography Acuity** | Euclidean Distance Transform (EDT) Stroke Width Variance | Identifies low-resolution typography reproduction and font mismatches. |
| **6** | **Texture Invariant** | 59-Bin Uniform Local Binary Patterns (LBP) $\chi^2$ Distance | Distinguishes original high-grade polymer substrate from cheaper substitutes. |
| **7** | **Heat-Seal Crimp Gradient** | Sobel $Y$ Derivative Frequency Across Top/Bottom Borders | Identifies illicit thermal iron reseals vs industrial pneumatic crimp patterns. |
| **8** | **Print Quality & Bleed** | High-Frequency Sobel Gradient Magnitude + Fringing Index | Detects home inkjet/laser printing artifacts on counterfeit packaging. |
| **9** | **Structured Text OCR** | Tesseract OCR + Regular Expression Information Extraction | Automatically extracts MRP, Batch Number, Manufacturing Date, and Expiry. |
| **10** | **Barcode Syntactic Check** | ZXing Computer Vision Decoder + EAN-13 Modulo-10 Checksum | Flags forged or spoofed retail barcodes. |
| **11** | **Phishing QR Whitelist** | ZXing 2D Matrix Decoder + Domain Whitelist Matching | Rejects deceptive URLs and phishing domains disguised as brand feedback portals. |
| **12** | **FSSAI Regulatory Engine** | 14-Digit Syntax Validation + Indian State Jurisdiction Mapping | Detects invalid food safety registration license numbers. |

---

## 💻 Tech Stack & Engineering Standards

* **Backend**: Python 3.10+, FastAPI (Asynchronous Web Framework), Pydantic v2.
* **ORM & Database**: SQLAlchemy 2.0, Alembic, PostgreSQL 18.6 (Primary), `asyncpg` + `psycopg2`.
* **Computer Vision & AI**: OpenCV 4.x, NumPy, SciPy, PyTorch, Tesseract OCR, ZXing.
* **Frontend**: React 19, TypeScript, Vite, TailwindCSS v4, Lucide Icons, Axios.
* **Report Generation**: ReportLab (Vector Graphics & Formatted PDF Generation).
* **Testing & MLOps**: Pytest, Pytest-AsyncIO, Custom Model Registry with Robustness Benchmarks.

---

## ⚡ Quickstart & Installation

### 1. Prerequisites
- **Python**: Version 3.10 or higher
- **Node.js**: Version 18 or higher (with npm)
- **Database**: PostgreSQL (or use the built-in SQLite fallback for quick testing)

### 2. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/pravashsingh775/VeriSure_Ai.git
cd VeriSure_Ai

# Install Python backend dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies and build assets
cd frontend
npm install
npm run build
cd ..
```

### 3. Environment Configuration
Copy the example environment file:
```bash
cp .env.example .env
```
*(The default `.env` is pre-configured with zero-friction development settings).*

### 4. Run Development Servers (1-Click)
On Windows:
```cmd
run_dev.bat
```
Or start manually:
```bash
# Terminal 1: Backend API
python -m uvicorn backend.app.main:app --reload --port 8000

# Terminal 2: Frontend Client
cd frontend && npm run dev
```

* 🌐 **Frontend Application**: `http://localhost:5173`
* 📖 **Interactive Swagger UI**: `http://localhost:8000/docs`
* ❤️ **System Health Endpoint**: `http://localhost:8000/health`

---

## 👥 Demo Role Accounts

Test all three stakeholder personas with one click in the web app or use these credentials:

| Portal Persona | Email | Password | Assigned Permissions |
|:---|:---|:---|:---|
| **Platform Admin** | `admin@verisure.ai` | `Admin@12345` | Full system access, case triage, MLOps model registry, audit logs |
| **Brand Admin (Amul)** | `amul_admin@verisure.ai` | `Amul@12345` | Brand packaging lifecycle, Reference Corpus V1, brand telemetry |
| **Brand Reviewer** | `reviewer@verisure.ai` | `Reviewer@12345` | Suspicious case evaluation, manual annotations, feedback loop |
| **Consumer** | `consumer@verisure.ai` | `Consumer@12345` | Real-time scan upload, difference viewer, PDF report downloads |

---

## 🧪 Automated Testing & Verification

VeriSure AI enforces rigorous automated testing with automated test isolation:
```bash
# Run the complete test suite against PostgreSQL
python -m pytest backend/tests/ -v
```

```
============================== test session starts ==============================
backend/tests/test_counterfeit_detection.py ........ [ 13%]
backend/tests/test_final_architecture.py ............ [ 33%]
backend/tests/test_phase15_to_18_apis.py ............ [ 47%]
backend/tests/test_phase1_models_and_db.py .......... [ 58%]
backend/tests/test_phase2_3_4_apis.py ............... [ 75%]
backend/tests/test_phase5_to_11_pipeline.py ......... [100%]

======================== 36 passed in 70.45s (0:01:10) ========================
```

---

## 📁 Repository Directory Structure

```
VeriSure_Ai/
├── backend/
│   ├── app/
│   │   ├── ai/               # 12 Evidence Engines, Fusion, Orchestrator
│   │   ├── api/              # FastAPI v1 Route Handlers & RBAC Dependencies
│   │   ├── core/             # Configuration, PostgreSQL Database, Local Storage
│   │   ├── models/           # SQLAlchemy Enterprise Entity Relational Schema
│   │   ├── schemas/          # Pydantic v2 Serialization & Validation Schemas
│   │   └── services/         # Business Logic, Scan Processing, PDF Reports
│   ├── migrations/           # Alembic Database Migration Revisions
│   ├── scripts/              # Seed Scripts & Database Hygiene Automation
│   └── tests/                # 36 Pytest Integration & Regression Suites
├── frontend/
│   ├── src/
│   │   ├── components/       # UI: Scanner, DifferenceViewer, Brand & Admin Portals
│   │   ├── services/         # Axios API Client & Authentication Handlers
│   │   └── types/            # TypeScript Domain Interfaces
├── data/
│   └── storage/
│       └── references/       # Reference Corpus V1 Official Amul Standard Assets
├── docs/                     # System Architecture, ER Diagrams, & Forensic Audits
├── run_dev.bat               # 1-Click Multi-Process Development Launcher
├── run_prod.py               # Unified Single-Process Production Server
└── README.md                 # Project Showcase & Documentation
```

---

## ⚖️ Academic & Legal Disclaimer

*VeriSure AI is an artificial-intelligence-assisted packaging conformity assessment tool designed for anti-counterfeiting research and brand protection. A photograph evaluates exterior packaging, print, and seal integrity; it cannot analyze or guarantee the chemical, nutritional, or microbiological contents inside a sealed container.*

---

<p align="center">
  <b>Engineered with precision for modern FMCG brand protection.</b><br>
  Developed by <b>Pravash Singh</b>
</p>


