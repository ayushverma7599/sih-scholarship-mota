"""File storage behind an interface so local disk can be swapped for S3 later."""
from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from app.core.config import settings


class Storage:
    def save(self, data: bytes, filename: str, subdir: str = "") -> str: ...
    def path(self, key: str) -> str: ...


class LocalStorage(Storage):
    def __init__(self, base: str | None = None):
        self.base = Path(base or settings.UPLOAD_DIR)
        self.base.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, filename: str, subdir: str = "") -> str:
        ext = Path(filename).suffix.lower()
        key = f"{subdir}/{uuid.uuid4().hex}{ext}" if subdir else f"{uuid.uuid4().hex}{ext}"
        dest = self.base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return str(dest)

    def path(self, key: str) -> str:
        return key if os.path.isabs(key) else str(self.base / key)


# S3Storage would implement the same interface (boto3) — stubbed for hackathon.
def get_storage() -> Storage:
    return LocalStorage()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
