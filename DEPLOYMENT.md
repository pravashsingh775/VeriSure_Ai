# VeriSure AI — Production Deployment & Containerization Guide

---

## 1. Containerized Deployment with Docker Compose

VeriSure provides an integrated container configuration connecting the FastAPI backend, pre-built Vite frontend, and a PostgreSQL 16 relational database:

```bash
# 1. Build and start containers in detached mode
docker compose up -d --build

# 2. View running containers
docker compose ps

# 3. Stream backend logs
docker compose logs -f backend
```

---

## 2. Docker Architecture

* **Database Service (`postgres`)**:
  * Image: `postgres:16-alpine`
  * Persistent volume: `postgres_data:/var/lib/postgresql/data`
  * Built-in healthcheck: `pg_isready -U verisure_app -d verisure_db`
* **Backend Service (`backend`)**:
  * Python 3.10+ container running Uvicorn ASGI server on port 8000
  * Connected to PostgreSQL via `DATABASE_URL=postgresql+asyncpg://...`
  * Mounts `./data/storage` for persistent image and report storage.

---

## 3. Production Environment Checklist

Before deploying to public production infrastructure:

1. **Generate Strong Secrets**:
   ```bash
   # Generate high-entropy 256-bit secret key
   openssl rand -hex 32
   ```
   Set `SECRET_KEY` in `.env`.
2. **Switch Database to PostgreSQL**:
   ```env
   DATABASE_URL=postgresql+asyncpg://verisure_app:your_password@localhost:5432/verisure_db
   DATABASE_SYNC_URL=postgresql://verisure_app:your_password@localhost:5432/verisure_db
   ```
3. **Configure Strict CORS**:
   Replace wildcard origins with the exact production domain names:
   ```env
   CORS_ORIGINS=https://verisure.yourdomain.com
   ```
4. **Set Production Mode**:
   ```env
   ENVIRONMENT=production
   DEBUG=False
   ```
5. **Run Alembic Migrations**:
   ```bash
   python -m alembic upgrade head
   ```

---

## 4. Health & Observability

* **Liveness Probe**: `GET /health` returns `{ "status": "healthy", "service": "verisure-api" }`
* **Readiness Probe**: Checks active database connection pool availability.

