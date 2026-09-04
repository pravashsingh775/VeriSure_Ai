# VeriSure AI — REST API Documentation (v1)

Base URL: `http://localhost:8000/api/v1`  
Interactive Swagger UI: `http://localhost:8000/docs`  
OpenAPI Specification: `http://localhost:8000/openapi.json`

---

## 1. Authentication & Users (`/auth`)

### `POST /auth/login`
Authenticates a user and issues a Bearer JWT access token.
* **Request Body**:
  ```json
  {
    "email": "admin@verisure.ai",
    "password": "Admin@12345"
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": {
      "id": "uuid-string",
      "email": "admin@verisure.ai",
      "full_name": "Platform Administrator",
      "roles": ["PLATFORM_ADMIN"],
      "brand_id": null
    }
  }
  ```

### `GET /auth/me`
Returns current authenticated user profile.
* **Headers**: `Authorization: Bearer <token>`
* **Response (200 OK)**: User profile object.

---

## 2. Product Catalog (`/products`)

### `GET /products`
Lists all registered products and their variants/pack sizes.
* **Query Params**: `brand_id` (optional, string)
* **Response (200 OK)**:
  ```json
  [
    {
      "id": "prod-uuid",
      "name": "Amul Taaza",
      "category": "MILK",
      "is_active": true,
      "variants": [
        {
          "id": "var-uuid",
          "variant_name": "Toned Milk",
          "fat_content": "3.0%",
          "snf_content": "8.5%",
          "pack_sizes": [
            {
              "id": "ps-uuid",
              "pack_size": "500ml",
              "pack_type": "POUCH",
              "net_quantity": "500 ml"
            }
          ]
        }
      ]
    }
  ]
  ```

---

## 3. Packaging Versions (`/packaging-versions`)

### `GET /packaging-versions`
Lists all packaging versions and expected packaging rules.
* **Query Params**: `pack_size_id` (optional), `status` (optional)
* **Response (200 OK)**: Array of version objects with `expected_mrp`, `expected_barcode`, `status` (`DRAFT`, `APPROVED`, `ACTIVE`, `DEPRECATED`).

### `POST /packaging-versions`
Creates a new packaging version (Requires `BRAND_ADMIN`).

---

## 4. Product Scanning & Verification (`/scans`)

### `POST /scans/upload`
Uploads a product photograph for end-to-end authenticity risk assessment.
* **Content-Type**: `multipart/form-data`
* **Form Fields**:
  * `file`: Binary image file (JPEG/PNG, max 15MB)
  * `view_type`: `FRONT` | `BACK` | `SIDE` | `DETAIL`
  * `is_multi_angle`: `true` | `false`
* **Response (201 Created)**:
  ```json
  {
    "id": "scan-uuid",
    "status": "REPORT_READY",
    "identified_product_name": "Amul Taaza",
    "identified_variant_name": "Toned Milk",
    "identified_pack_size": "500ml",
    "packaging_version_code": "V1",
    "images": [
      {
        "id": "img-uuid",
        "view_type": "FRONT",
        "image_path": "raw_scans/scan_uuid_front_amul_taaza.png",
        "crop_path": "crops/crop_uuid_front.png",
        "heatmap_path": "heatmaps/heatmap_uuid_front.png",
        "quality_score": 0.88,
        "quality_details": {
          "usable": true,
          "blur_score": 0.92,
          "brightness_score": 0.89,
          "glare_score": 0.94
        }
      }
    ],
    "evidences": [
      {
        "type": "logo",
        "score": 0.94,
        "confidence": 0.91,
        "availability": true,
        "quality": 0.89,
        "source": "logo-orb-v1",
        "explanation": "Amul logo matched genuine reference template with 94.0% confidence."
      }
    ],
    "decision": {
      "state": "LOW_RISK",
      "risk_score": 14.5,
      "confidence": 0.91,
      "uncertainty": 0.09,
      "evidence_coverage": 0.85,
      "recommendation": "Packaging markers conform to genuine specifications.",
      "explanation_summary": "Packaging layout and logo keypoints strongly match authorized reference...",
      "contradictions": [],
      "suspicious_regions": []
    },
    "report_url": "reports/report_uuid.pdf",
    "created_at": "2026-09-03T19:30:00Z"
  }
  ```

### `GET /scans/{scan_id}`
Retrieves full verification results for a previous scan.

### `GET /scans/{scan_id}/report`
Streams the generated cryptographic PDF certificate file directly to the client.

### `GET /scans/history/me`
Retrieves consumer's private scan history.

---

## 5. Suspicious Case Management (`/cases`)

### `GET /cases`
Lists all triaged suspicious cases (Requires `BRAND_ADMIN`, `BRAND_REVIEWER`, or `PLATFORM_ADMIN`).
* **Query Params**: `status`, `priority`

### `POST /cases/{case_id}/review`
Performs human-in-the-loop review on a suspicious scan.
* **Request Body**:
  ```json
  {
    "new_status": "VERIFIED_SUSPICIOUS",
    "comments": "Confirmed secondary ironed reseal along bottom crimp seam."
  }
  ```

---

## 6. Feedback & Learning (`/feedback`)

### `POST /feedback`
Submits user or expert feedback on a scan.
* **Fields**: `scan_id`, `origin_type` (`SCAN`, `CASE`, `DATASET_REVIEW`, `REFERENCE_AUDIT`), `verified_label`, `notes`.

---

## 7. Model Registry & MLOps (`/models`)

### `GET /models`
Lists all vision and evidence models, their versions, statuses, and evaluation metrics.

### `POST /models/versions/{version_id}/evaluate`
Triggers an offline evaluation run with perturbation simulations (glare, blur, noise).

---

## 8. Analytics & Metrics (`/analytics`)

### `GET /analytics/admin`
Returns platform-wide operational metrics: total scans, suspicious case rate, quality gate pass percentage, and anomaly distributions.

