# VeriSure AI — Local Zero-Cost Setup Guide

This guide describes how to set up, configure, and execute the complete VeriSure AI platform locally at **₹0 software and API cost**.

---

## 1. Prerequisites

Ensure the following tools are installed on your machine:
* **Python 3.10+**: [Download Python](https://www.python.org/downloads/) (ensure "Add Python to PATH" is checked during installation)
* **Node.js 18+ and npm**: [Download Node.js](https://nodejs.org/)
* **Git**: [Download Git](https://git-scm.com/)

---

## 2. Repository Setup

```bash
# Clone the repository
git clone https://github.com/your-username/VeriSure_Ai.git
cd VeriSure_Ai

# Verify Python installation
python --version
# Expected: Python 3.10.x or higher

# Verify Node installation
node --version
npm --version
```

---

## 3. Backend Setup (Python & FastAPI)

### 3.1. Install Python Dependencies
```bash
# Install required dependencies
pip install -r backend/requirements.txt
```

### 3.2. Configure Environment Variables
Copy the environment template:
```bash
# Windows PowerShell
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

The default `.env` is pre-configured for local development with SQLite (`verisure.db`). No cloud API keys or external paid accounts are required.

### 3.3. Initialize & Seed Database
Initialize the database schema and seed the default roles, test users, and the Amul milk catalog:
```bash
# Apply migrations to head
python -m alembic upgrade head

# Seed catalog and roles
python -m backend.scripts.seed_data

# Seed model registry metadata
python -m backend.scripts.seed_models
```

---

## 4. Frontend Setup (React, Vite & TypeScript)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build production assets
npm run build

# Return to root
cd ..
```

---

## 5. Running the Application

### Method A: Single-Command Production Server (Recommended)
Run the unified FastAPI server that serves both the API backend and the pre-built React frontend:
```bash
python run_prod.py
```
* **Web Application**: [http://localhost:8000/app](http://localhost:8000/app)
* **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **System Health Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

### Method B: Dual-Terminal Development Mode
If actively developing the frontend with hot-module reloading:
* **Terminal 1 (Backend)**:
  ```bash
  uvicorn backend.app.main:app --reload --port 8000
  ```
* **Terminal 2 (Frontend)**:
  ```bash
  cd frontend
  npm run dev
  ```
  Access frontend at: [http://localhost:5173](http://localhost:5173)

---

## 6. Default Demo Credentials

| Role | Email | Password | Access Scope |
|---|---|---|---|
| **Platform Admin** | `admin@verisure.ai` | `Admin@12345` | Global admin dashboard, MLOps, model registry, case review |
| **Brand Admin** | `amul_admin@verisure.ai` | `Amul@12345` | Amul brand portal, packaging versions, reference catalog |
| **Consumer** | `consumer@verisure.ai` | `Consumer@12345` | Product scanning, scan history, PDF report download |

---

## 7. Running the Automated Test Suite

To verify that all models, APIs, and evidence engines are functioning correctly:
```bash
# Run the complete test suite
python -m pytest backend/tests/ -v
```
Expected output: **24+ passed (100%), 0 failed**.

