# VeriSure AI — Production Performance Baseline & Capacity Report

**Document ID**: `PERF-BASE-2026-09`  
**Evaluation Date**: September 5, 2026  
**Auditor**: Senior Principal SRE & Performance Engineer  
**Source Artifact**: `artifacts/performance/baseline_metrics.json`  

---

## 1. Test Environment & System Specifications

| Parameter | Specification |
| :--- | :--- |
| **Operating System** | Windows 11 AMD64 (Host) / Ubuntu 24.04 LTS (WSL2 Database Engine) |
| **Python Runtime** | Python 3.10.0 64-bit (`MSC v.1929 64 bit (AMD64)`) |
| **Database Engine** | PostgreSQL 18.6 (x86_64-pc-linux-gnu, Ubuntu 18.6-1.pgdg24.04+1) |
| **Database Driver** | AsyncPG 0.30.0 / SQLAlchemy 2.0.44 |
| **Application Server**| FastAPI 0.115.6 + Uvicorn 0.34.0 |
| **AI Runtime** | PyTorch 2.0+ CPU, Torchvision, OpenCV 4.10, EasyOCR |
| **Memory Baseline** | 116.03 MB (Initial) &rarr; 412.46 MB (Post-Benchmark) &Delta; 296.43 MB |
| **CPU Utilization** | Average 24.0% &ndash; 78.5% peak during dual-scan fusion |

---

## 2. Workload Concurrency & Latency Benchmarks

All tests were executed against the live application using `httpx.AsyncClient` under multi-client concurrency. All metrics below represent empirical observations from `artifacts/performance/baseline_metrics.json`.

| Workload Category | Concurrency ($C$) | Total Requests ($N$) | Duration (s) | Throughput (RPS) | Latency p50 (ms) | Latency p95 (ms) | Latency p99 (ms) | Error Rate (%) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **System Liveness (`/liveness`)** | 25 | 50 | 2.39 | **20.90** | 1,189.41 | 1,340.93 | 1,352.59 | **0.00%** | PASS |
| **User Authentication (`/auth/login`)** | 10 | 20 | 7.81 | **2.56** | 3,899.46 | 3,978.49 | 3,984.82 | **0.00%** | PASS |
| **Catalog Metadata (`/products`)** | 25 | 50 | 2.77 | **18.04** | 1,375.72 | 1,549.90 | 1,571.72 | **0.00%** | PASS |
| **Single-Panel AI Scan (`/scans/upload`)** | 5 | 10 | 89.96 | **0.11** | 44,963.82 | 50,162.12 | 50,166.08 | **0.00%** | PASS* |
| **Dual-Panel 360° AI Scan (`/scans/dual`)** | 3 | 6 | 38.72 | **0.15** | 19,359.22 | 19,416.66 | 19,417.25 | **0.00%** | PASS* |
| **PDF Audit Report (`/scans/{id}/report`)** | 5 | 10 | 1.83 | **5.47** | 903.78 | 1,409.80 | 1,410.92 | **0.00%** | PASS |

*\* Note: Heavy computer vision workloads are currently bound to CPU execution without dedicated GPU tensor cores.*

---

## 3. Workload Analysis & Deep-Dive Findings

### 3.1 Authentication & Cryptographic Hashing
- **Throughput**: 2.56 RPS at Concurrency 10.
- **Latency**: p50 = 3.90s, p95 = 3.98s.
- **Root Cause**: VeriSure AI implements industry-standard `bcrypt` password hashing with a security cost factor of 12 (`rounds=12`), which intentionally requires ~350ms of CPU compute per password verification to protect against dictionary and offline brute-force attacks.

### 3.2 Metadata & Health Endpoints
- **Liveness & Readiness**: 20.90 RPS under 25 concurrent connections with zero socket errors or dropped packets.
- **Database Connection Pool**: AsyncPG handles concurrent connection acquisition within 8ms. Pool size configured at `min_size=5, max_size=20`.

### 3.3 Computer Vision & Evidence Fusion Pipeline
- **Single Scan**: 10 requests processed sequentially across 5 concurrent workers required ~45.0s per request.
- **Dual Scan**: 6 requests across 3 workers averaged 19.36s per request.
- **Component Breakdown**:
  - Image decoding & normalization: ~8% (~1.5s)
  - ORB homography & keypoint matching: ~22% (~4.2s)
  - SSIM difference heatmap synthesis: ~15% (~2.9s)
  - Color space delta & histogram calculation: ~10% (~1.9s)
  - Barcode EAN-13 & FSSAI OCR extraction: ~35% (~6.8s)
  - Evidential Deep Fusion & Uncertainty estimation: ~10% (~1.9s)

---

## 4. Production Bottleneck Analysis & Scale-Out Roadmap

1. **Synchronous CPU Vision Processing**:
   - *Current State*: Inference is executed synchronously within the FastAPI worker thread pool.
   - *Production Architecture*: For enterprise production deployment (>10,000 scans/day), offload image ingestion to an asynchronous worker queue (Celery/Redis or RabbitMQ) with CUDA GPU nodes running TensorRT or ONNX Runtime.
2. **PostgreSQL Read Replicas**:
   - Read queries for catalog metadata, packaging specifications, and reference manifests should be directed to read-replicas or cached in Redis with a 5-minute TTL.
3. **Storage Latency**:
   - Current local disk I/O latency is negligible (<2ms). Cloud deployments should utilize S3/GCS with CDN caching for reference standards.

