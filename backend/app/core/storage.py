import asyncio
import os
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from backend.app.core.config import settings


class BaseStorage(ABC):
    """
    Abstract storage provider interface for local disk, AWS S3, or GCP Cloud Storage.
    """
    @abstractmethod
    async def save_bytes(self, data: bytes, subfolder: str, filename: str | None = None, extension: str = ".png") -> tuple[str, str]:
        """Returns (relative_path, absolute_path)"""
        pass

    @abstractmethod
    def get_absolute_path(self, relative_path: str) -> Path:
        pass

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        pass

    @abstractmethod
    def delete(self, relative_path: str) -> bool:
        pass


class LocalStorage(BaseStorage):
    """
    Local filesystem storage with path traversal protection and directory isolation.
    """
    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or settings.storage_path
        self._ensure_directories()

    def _ensure_directories(self):
        subdirs = [
            "raw_scans",
            "crops",
            "heatmaps",
            "references",
            "references_v2",
            "synthetic_tampers",
            "negative_samples",
            "reports",
            "artifacts",
            "temp"
        ]
        for sub in subdirs:
            (self.base_path / sub).mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        # Strip path traversal and weird chars
        filename = os.path.basename(filename)
        cleaned = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        return cleaned or f"file_{uuid.uuid4().hex[:8]}"

    def _resolve_safe_path(self, relative_path: str) -> Path:
        target = (self.base_path / relative_path).resolve()
        base = self.base_path.resolve()
        # Robust cross-platform path traversal guard
        try:
            if os.path.commonpath([str(target), str(base)]) != str(base):
                raise ValueError(f"Illegal path traversal attempt: {relative_path}")
        except ValueError as err:
            raise ValueError(f"Illegal path traversal attempt: {relative_path}") from err
        return target

    async def save_bytes(
        self,
        data: bytes,
        subfolder: str,
        filename: str | None = None,
        extension: str = ".png"
    ) -> tuple[str, str]:
        folder = self.base_path / subfolder
        folder.mkdir(parents=True, exist_ok=True)

        if not filename:
            filename = f"{uuid.uuid4().hex}{extension}"
        else:
            filename = self._sanitize_filename(filename)
            if not filename.endswith(extension) and extension:
                filename = f"{filename}{extension}"

        rel_path = f"{subfolder}/{filename}".replace("\\", "/")
        abs_path = self._resolve_safe_path(rel_path)

        await asyncio.to_thread(abs_path.write_bytes, data)

        return rel_path, str(abs_path)

    def get_absolute_path(self, relative_path: str) -> Path:
        return self._resolve_safe_path(relative_path)

    def exists(self, relative_path: str) -> bool:
        try:
            return self._resolve_safe_path(relative_path).exists()
        except Exception:
            return False

    def delete(self, relative_path: str) -> bool:
        try:
            path = self._resolve_safe_path(relative_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False


storage = LocalStorage()
