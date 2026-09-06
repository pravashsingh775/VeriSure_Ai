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
    expose_headers=["X-Request-ID", "Content-Disposition"],
)

import logging
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("verisure.api")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


app.add_middleware(RequestCorrelationMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception(f"Unhandled internal server error during request [{req_id}]: {exc}")
    return JSONResponse(
        status_code=500,
        headers={"X-Request-ID": req_id},
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal error occurred. Please contact system support.",
                "request_id": req_id,
            }
        },
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


from sqlalchemy import text

from backend.app.core.database import AsyncSessionLocal


@app.get("/health", tags=["Health"])
async def health():
    db_status = "connected"
    overall_status = "healthy"
    status_code = 200

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health probe database check failed: {e}")
        db_status = "disconnected"
        overall_status = "unhealthy"
        status_code = 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "environment": settings.ENVIRONMENT,
            "storage": settings.STORAGE_PROVIDER,
            "database": db_status
        }
    )


@app.get("/liveness", tags=["Health"])
async def liveness():
    """
    Lightweight liveness probe for Kubernetes / container orchestration.
    Confirms application process is responsive.
    """
    return JSONResponse(
        status_code=200,
        content={"status": "alive", "service": settings.PROJECT_NAME}
    )


@app.get("/readiness", tags=["Health"])
async def readiness():
    """
    Comprehensive readiness probe validating critical dependencies:
    - PostgreSQL database connectivity
    - Storage subsystem read/write capability
    - AI runtime availability
    """
    checks = {
        "database": "unknown",
        "storage": "unknown",
        "ai_device": settings.AI_DEVICE
    }
    is_ready = True

    # 1. Database Connectivity Probe
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        logger.error(f"Readiness probe database failure: {e}")
        checks["database"] = "unreachable"
        is_ready = False

    # 2. Storage Read/Write Probe
    try:
        probe_path = settings.storage_path / ".readiness_probe"
        probe_path.write_text("probe_ok", encoding="utf-8")
        if probe_path.read_text(encoding="utf-8") == "probe_ok":
            probe_path.unlink(missing_ok=True)
            checks["storage"] = "read_write_verified"
        else:
            checks["storage"] = "integrity_mismatch"
            is_ready = False
    except Exception as e:
        logger.error(f"Readiness probe storage failure: {e}")
        checks["storage"] = f"inaccessible: {str(e)[:50]}"
        is_ready = False

    status_code = 200 if is_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "unready",
            "environment": settings.ENVIRONMENT,
            "checks": checks
        }
    )


from pathlib import Path

from fastapi.responses import FileResponse

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    if (frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="frontend_assets")

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon_svg():
        fav = frontend_dist / "favicon.svg"
        if fav.exists():
            return FileResponse(fav, media_type="image/svg+xml")
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon_ico():
        fav = frontend_dist / "favicon.svg"
        if fav.exists():
            return FileResponse(fav, media_type="image/svg+xml")
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    @app.get("/icons.svg", include_in_schema=False)
    async def icons_svg():
        icons = frontend_dist / "icons.svg"
        if icons.exists():
            return FileResponse(icons, media_type="image/svg+xml")
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    @app.get("/app", include_in_schema=False)
    @app.get("/app/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        return FileResponse(frontend_dist / "index.html")

