from typing import Any, List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "VeriSure AI"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on", "t", "dev", "development")
        return bool(v)

    # Security
    SECRET_KEY: str = "verisure-development-secret-key-change-in-production-demo"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def reject_insecure_secret_in_production(cls, v: str) -> str:
        """Refuse to boot with the well-known development key outside development.

        A publicly-known JWT signing key in production lets anyone forge admin
        tokens, so this fails fast instead of silently degrading security.
        """
        import os
        environment = os.getenv("ENVIRONMENT", "development").lower()
        insecure_defaults = {
            "verisure-development-secret-key-change-in-production-demo",
            "change-this-in-production-with-openssl-rand-hex-32",
        }
        if environment not in ("development", "dev", "local", "test", "testing") and v in insecure_defaults:
            raise ValueError(
                "REFUSING TO START: SECRET_KEY is still the insecure development default. "
                "Set a strong SECRET_KEY environment variable in production "
                "(e.g. python -c \"import secrets; print(secrets.token_hex(32))\")."
            )
        return v

    # PostgreSQL Configuration (Primary)
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: Optional[str] = None

    # Database URLs (PostgreSQL Primary, with SQLite fallback support for isolated tests)
    DATABASE_URL: str = "postgresql+asyncpg://verisure_app:verisure_secure_pass_2026@localhost:5432/verisure_db"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://verisure_app:verisure_secure_pass_2026@localhost:5432/verisure_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_async_db_url(cls, v: Optional[str], info) -> str:
        if isinstance(v, str) and v.strip():
            return v
        values = info.data
        user = values.get("POSTGRES_USER")
        password = values.get("POSTGRES_PASSWORD")
        host = values.get("POSTGRES_HOST")
        port = values.get("POSTGRES_PORT", 5432)
        db = values.get("POSTGRES_DB")
        if user and password and host and db:
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
        return "postgresql+asyncpg://verisure_app:verisure_secure_pass_2026@localhost:5432/verisure_db"

    @field_validator("DATABASE_SYNC_URL", mode="before")
    @classmethod
    def assemble_sync_db_url(cls, v: Optional[str], info) -> str:
        if isinstance(v, str) and v.strip():
            return v
        values = info.data
        user = values.get("POSTGRES_USER")
        password = values.get("POSTGRES_PASSWORD")
        host = values.get("POSTGRES_HOST")
        port = values.get("POSTGRES_PORT", 5432)
        db = values.get("POSTGRES_DB")
        if user and password and host and db:
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
        return "postgresql+psycopg2://verisure_app:verisure_secure_pass_2026@localhost:5432/verisure_db"


    # Storage
    STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_DIR: str = "./data/storage"
    MAX_UPLOAD_SIZE_MB: int = 15

    # AI Device & Engine Settings
    AI_DEVICE: str = "cpu"
    OCR_CONFIDENCE_THRESHOLD: float = 0.50
    QUALITY_MIN_SCORE: float = 0.60
    FUSION_WEIGHTS_VERSION: str = "v1.0"
    DECISION_RULES_VERSION: str = "v1.0"
    AUTHORIZED_QR_DOMAINS: List[str] = ["amul.com", "gcmmf.com", "amuldairy.com"]

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
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

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent.parent

    @property
    def storage_path(self) -> Path:
        path = Path(self.STORAGE_LOCAL_DIR)
        if not path.is_absolute():
            path = self.base_dir / path
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
