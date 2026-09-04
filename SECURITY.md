# VeriSure AI — Security Architecture & Threat Model

---

## 1. Authentication & Session Security

* **Password Hashing**: Industry-standard **PBKDF2-HMAC-SHA256** with 600,000 iterations via `passlib.context.CryptContext`.
* **JWT Tokens**: Signed using HMAC-SHA256 (`HS256`) with a configurable secret key (`SECRET_KEY`).
* **Expiration Policy**: Access tokens expire in 1,440 minutes (24 hours).
* **Zero Hardcoded Secrets**: Secrets are sourced strictly from environment variables via Pydantic `BaseSettings`. Placeholder values in `.env.example` must be replaced with `openssl rand -hex 32` before public deployment.

---

## 2. Role-Based Access Control (RBAC)

VeriSure implements tenant-isolated RBAC enforced at the API dependency layer (`backend/app/api/deps.py`):

| Role | Scope | Permitted Endpoints & Capabilities |
|---|---|---|
| `CONSUMER` | Global / Self | Upload scans, inspect private scan history (`/scans/history/me`), download own PDF reports. |
| `BRAND_ADMIN` | Brand Tenant | Manage brand catalog, upload/approve packaging versions, view brand analytics, triage brand cases. |
| `BRAND_REVIEWER`| Brand Tenant | Review and transition suspicious cases assigned to the brand. |
| `PLATFORM_ADMIN`| Global | Manage all brands, users, global model registry, system-wide analytics, and audit log inspection. |

**Tenant Isolation Enforcement**: Brand administrators and reviewers cannot access or modify packaging versions, products, or suspicious cases belonging to other brands.

---

## 3. Input Validation & Storage Hardening

* **MIME-Type & Magic Byte Validation**: Only `image/jpeg` and `image/png` uploads are permitted. Magic bytes (`\xFF\xD8\xFF` for JPEG, `\x89PNG` for PNG) are validated during decoding via OpenCV.
* **File Size Constraints**: Maximum upload size is enforced at 15 MB (`MAX_UPLOAD_SIZE_MB`).
* **Path Traversal Prevention**: Storage paths are generated using UUIDv4 filenames. User-supplied filenames are never used as physical storage filenames on disk.
* **SQL Injection Immunity**: All database queries utilize SQLAlchemy 2.0 async parameterized statements and ORM mappings. Zero raw string SQL concatenation exists in the application.

---

## 4. Audit Logging

Every critical security event is persisted in an append-only audit trail (`backend/app/core/audit.py`):
* User logins & authentication failures
* Product & packaging version modifications
* Packaging reference approvals
* Suspicious case reviews & status transitions
* Model approvals & deployment configurations

