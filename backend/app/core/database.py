import sys
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import Column, DateTime, String, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.core.config import settings

is_sqlite = "sqlite" in settings.DATABASE_SYNC_URL or "sqlite" in settings.DATABASE_URL

if is_sqlite:
    # Async Engine for SQLite
    async_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
    )
    # Sync Engine for SQLite
    sync_engine = create_engine(
        settings.DATABASE_SYNC_URL,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
else:
    # Production Async Engine for PostgreSQL with NullPool for robust multi-loop & test safety
    async_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    # Production Sync Engine for PostgreSQL with connection pooling
    sync_engine = create_engine(
        settings.DATABASE_SYNC_URL,
        echo=False,
        future=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


class BaseModel(Base):
    """
    Abstract base model providing UUID primary key and audit timestamps.
    """
    __abstract__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession per request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initializes database tables asynchronously.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
