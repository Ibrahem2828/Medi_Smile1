# apps/attachments/storage_backends.py
from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from typing import BinaryIO

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.translation import gettext_lazy as _


# ============================================================
# Base Storage Interface
# ============================================================
class BaseStorageBackend(ABC):
    """
    Abstract storage backend interface.
    """

    @abstractmethod
    def save(self, name: str, content: BinaryIO) -> str:
        raise NotImplementedError

    @abstractmethod
    def delete(self, name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def url(self, name: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def open(self, name: str, mode: str = "rb"):
        raise NotImplementedError


# ============================================================
# Local Storage Backend
# ============================================================
class LocalStorageBackend(BaseStorageBackend):
    """
    Local filesystem storage backend.
    """

    def __init__(self, base_location: str | None = None):
        self.base_location = base_location or settings.PRIVATE_MEDIA_ROOT
        self.storage = FileSystemStorage(location=self.base_location)

    def save(self, name: str, content: BinaryIO) -> str:
        return self.storage.save(name, content)

    def delete(self, name: str) -> None:
        if self.storage.exists(name):
            self.storage.delete(name)

    def exists(self, name: str) -> bool:
        return self.storage.exists(name)

    def url(self, name: str) -> str:
        return self.storage.url(name)

    def open(self, name: str, mode: str = "rb"):
        return self.storage.open(name, mode)


class S3StorageBackend(BaseStorageBackend):
    """Thin adapter around the configured S3 storage.

    This must not inherit ``LocalStorageBackend``: doing so runs the local
    constructor and silently replaces S3 with ``FileSystemStorage``.
    """

    def __init__(self):
        from storages.backends.s3boto3 import S3Boto3Storage

        self.storage = S3Boto3Storage()

    def save(self, name: str, content: BinaryIO) -> str:
        return self.storage.save(name, content)

    def delete(self, name: str) -> None:
        if self.storage.exists(name):
            self.storage.delete(name)

    def exists(self, name: str) -> bool:
        return self.storage.exists(name)

    def url(self, name: str) -> str:
        return self.storage.url(name)

    def open(self, name: str, mode: str = "rb"):
        return self.storage.open(name, mode)


# ============================================================
# Storage Resolver
# ============================================================
def get_storage_backend() -> BaseStorageBackend:
    """
    Resolve storage backend based on settings.

    Uses Django's current storage setting.  ``DEFAULT_FILE_STORAGE`` was
    removed in Django 5.1, so reading it here would fail after the upgrade.
    """
    backend = settings.STORAGES.get("default", {}).get("BACKEND", "")
    if backend.endswith("S3Boto3Storage"):
        return S3StorageBackend()

    return LocalStorageBackend(base_location=str(settings.PRIVATE_MEDIA_ROOT))


# ============================================================
# Helpers
# ============================================================
def generate_attachment_path(*, original_filename: str, prefix: str = "attachments") -> str:
    """
    Generate safe unique path for attachment files.
    """
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()

    return os.path.join(
        prefix,
        f"{uuid.uuid4().hex}{ext}",
    )
