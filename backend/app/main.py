from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.v1 import (
    analytics,
    audit,
    auth,
    brands,
    cases,
    datasets,
    feedback,
    models,
    packaging,
    products,
    references,
    scans,
)
from backend.app.core.config import settings
from backend.app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables
    await init_db()
    yield
    # Shutdown: clean up if needed


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "VeriSure AI: AI-Based Product Authenticity Risk Assessment & Brand Protection Platform.\n\n"
        "Provides multi-evidence verification, packaging versioning, reference registry, "
        "and explainable risk assessments."
    ),
    lifespan=lifespan,
    # Hide interactive API docs outside development to reduce attack surface.
    docs_url="/docs" if settings.ENVIRONMENT.lower() in ("development", "dev", "local", "test", "testing") else None,
    redoc_url="/redoc" if settings.ENVIRONMENT.lower() in ("development", "dev", "local", "test", "testing") else None,
)

# CORS Middleware
# Explicit allowed origins plus regex matching any localhost/127.0.0.1 port for dev flexibility
if isinstance(settings.CORS_ORIGINS, list) and settings.CORS_ORIGINS:
    origins = settings.CORS_ORIGINS
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication & RBAC"])
app.include_router(brands.router, prefix=f"{settings.API_V1_STR}/brands", tags=["Brands"])
app.include_router(products.router, prefix=f"{settings.API_V1_STR}/products", tags=["Products"])
app.include_router(packaging.router, prefix=f"{settings.API_V1_STR}/packaging-versions", tags=["Packaging Versions"])
app.include_router(references.router, prefix=f"{settings.API_V1_STR}/references", tags=["Reference Registry"])
app.include_router(scans.router, prefix=f"{settings.API_V1_STR}/scans", tags=["Scans & Verification"])
app.include_router(cases.router, prefix=f"{settings.API_V1_STR}/cases", tags=["Suspicious Case Management"])
app.include_router(feedback.router, prefix=f"{settings.API_V1_STR}/feedback", tags=["Curated Feedback & Active Learning"])
app.include_router(datasets.router, prefix=f"{settings.API_V1_STR}/datasets", tags=["Datasets & Versioning"])
app.include_router(models.router, prefix=f"{settings.API_V1_STR}/models", tags=["Model Registry & Evaluation"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["Analytics & Observability"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["Audit Logging"])

import os
from fastapi.staticfiles import StaticFiles
os.makedirs(settings.STORAGE_LOCAL_DIR, exist_ok=True)
app.mount("/data/storage", StaticFiles(directory=settings.STORAGE_LOCAL_DIR), name="storage")


@app.get("/", tags=["Root"])
async def root():
    return {
        "platform": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "operational",
        "message": "Welcome to VeriSure AI Authenticity Risk Assessment Platform"
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "storage": settings.STORAGE_PROVIDER,
        "database": "connected"
    }


from pathlib import Path
from fastapi.responses import FileResponse
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="frontend_assets")

    @app.get("/app", include_in_schema=False)
    @app.get("/app/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        return FileResponse(frontend_dist / "index.html")
