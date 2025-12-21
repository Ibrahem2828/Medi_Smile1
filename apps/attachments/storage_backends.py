# apps/attachments/storage_backends.py

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from typing import BinaryIO

from django.conf import settings
from django.core.files.storage import FileSystemStorage, default_storage
from django.utils.translation import gettext_lazy as _


# ============================================================
# Base Storage Interface
# ============================================================

class BaseStorageBackend(ABC):
    """
    Abstract storage backend interface.
    All storage backends must implement this interface.
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


# ============================================================
# Local File System Storage
# ============================================================

class LocalStorageBackend(BaseStorageBackend):
    """
    Local filesystem storage backend.
    Uses Django FileSystemStorage.
    """

    def __init__(self, base_location: str | None = None):
        self.base_location = base_location or settings.MEDIA_ROOT
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


# ============================================================
# S3 Storage Backend
# ============================================================

class S3StorageBackend(BaseStorageBackend):
    """
    Amazon S3 storage backend (via django-storages).
    """

    def __init__(self):
        try:
            from storages.backends.s3boto3 import S3Boto3Storage
        except ImportError as exc:
            raise ImportError(
                _("django-storages is required for S3 storage backend.")
            ) from exc

        self.storage = S3Boto3Storage()

    def save(self, name: str, content: BinaryIO) -> str:
        return self.storage.save(name, content)

    def delete(self, name: str) -> None:
        self.storage.delete(name)

    def exists(self, name: str) -> bool:
        return self.storage.exists(name)

    def url(self, name: str) -> str:
        return self.storage.url(name)


# ============================================================
# Storage Resolver
# ============================================================

def get_storage_backend() -> BaseStorageBackend:
    """
    Resolve storage backend based on settings.

    DEFAULT_FILE_STORAGE:
    - storages.backends.s3boto3.S3Boto3Storage -> S3
    - anything else -> Local
    """

    if settings.DEFAULT_FILE_STORAGE == "storages.backends.s3boto3.S3Boto3Storage":
        return S3StorageBackend()

    return LocalStorageBackend()


# ============================================================
# Helpers
# ============================================================

def generate_attachment_path(
    *,
    original_filename: str,
    prefix: str = "attachments",
) -> str:
    """
    Generate a safe, unique path for attachment files.

    Example:
    attachments/2025/01/uuid_filename.png
    """

    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()

    unique_name = f"{uuid.uuid4().hex}{ext}"

    return os.path.join(
        prefix,
        unique_name,
    )
