# VeriSure AI — REST API Documentation

> Base URL: `http://localhost:8000/api/v1`  
> OpenAPI Interactive Docs: `http://localhost:8000/docs`  
> ReDoc Specification: `http://localhost:8000/redoc`

---

## 1. Authentication & RBAC (`/auth`)

### `POST /auth/login`
Authenticates a user and issues an HMAC-SHA256 JWT bearer token.
- **Request Body**:
  ```json
  {
    "email": "consumer@verisure.ai",
    "password": "Consumer@12345"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": "828371e4...",
      "email": "consumer@verisure.ai",
      "full_name": "Demo Consumer",
      "roles": ["CONSUMER"]
    }
  }
  ```

### `GET /auth/me`
Returns current authenticated user details. Header: `Authorization: Bearer <token>`.

---

## 2. Scans & Authenticity Risk Assessment (`/scans`)

### `POST /scans/upload`
Uploads a product photograph for end-to-end verification.
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: Image binary (PNG, JPG, WEBP)
  - `view_type`: `"FRONT"`, `"BACK"`, `"SEAL_TOP"`, or `"BARCODE_CLOSEUP"`
- **Response `201 Created`**:
  ```json
  {
    "id": "scan_84f93a10",
    "status": "REPORT_READY",
    "identified_product_name": "Amul Taaza",
    "identified_variant_name": "Homogenised Toned Milk",
    "identified_pack_size": "1L",
    "packaging_version_code": "V1",
    "decision": {
      "state": "LIKELY_GENUINE",
      "risk_score": 6.5,
      "confidence": 0.885,
      "uncertainty": 0.125,
      "evidence_coverage": 0.83,
      "recommendation": "All evaluated visual, textual, and machine-readable markers align closely with genuine factory reference standards.",
      "reason_codes": ["LOGO_CONGRUENT", "BARCODE_VERIFIED"],
      "explanation_summary": "Overall risk score evaluated at 6.5/100 with confidence 88.5% and evidence coverage of 83.0%. No conflicting evidence detected.",
      "contradictions": []
    },
    "evidences": [
      {
        "type": "logo",
        "score": 0.94,
        "confidence": 0.92,
        "availability": true,
        "quality": 0.89,
        "source": "verisure-orb-homography-v1",
        "explanation": "Amul brand logo matches genuine geometry with 88.5% keypoint consensus."
      }
    ],
    "report_url": "/api/v1/scans/scan_84f93a10/report",
    "created_at": "2026-09-02T22:45:00Z"
  }
  ```

### `GET /scans/{scan_id}`
Returns complete scan detail, evidence objects, difference heatmap path, and decision.

### `GET /scans/{scan_id}/report`
Streams the vector PDF report generated via ReportLab (`Content-Type: application/pdf`).

### `GET /scans/history/me`
Returns scan history for the authenticated consumer with user privacy isolation.

---

## 3. Brand & Packaging Version Registry (`/packaging-versions`, `/references`)

### `GET /packaging-versions`
Lists all packaging versions across products.

### `POST /packaging-versions/{id}/status`
Transitions version state machine (`DRAFT` $\to$ `PENDING_REVIEW` $\to$ `APPROVED` $\to$ `ACTIVE` $\to$ `DEPRECATED`). Requires `BRAND_ADMIN` or `PLATFORM_ADMIN`.

### `POST /references/upload`
Uploads reference packaging template image with trust score mapping (`BRAND_PROVIDED`: 1.0, `OFFICIAL_PUBLIC_SOURCE`: 0.85).

---

## 4. Suspicious Case Management (`/cases`)

### `GET /cases`
Lists all triaged suspicious cases pending human review. Filterable by `brand_id` and `status`.

### `POST /cases/{case_id}/review`
Records a review transition and feedback comment:
- **Request Body**:
  ```json
  {
    "new_status": "VERIFIED_SUSPICIOUS",
    "comments": "Confirmed irregular seal ridges under stereomicroscope."
  }
  ```

---

## 5. Model Registry & Evaluation (`/models`)

### `GET /models`
Lists all registered models, version tags, and benchmark evaluation runs.

### `POST /models/versions/{version_id}/evaluate`
Triggers real-time evaluation calculating Accuracy, Precision, Recall, F1, ROC-AUC, and robustness metrics under simulated perturbations.

