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


# ============================================================
# Local Storage Backend
# ============================================================
class LocalStorageBackend(BaseStorageBackend):
    """
    Local filesystem storage backend.
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
# Storage Resolver
# ============================================================
def get_storage_backend() -> BaseStorageBackend:
    """
    Resolve storage backend based on settings.

    DEFAULT_FILE_STORAGE:
    - S3 → cloud
    - otherwise → local filesystem
    """
    if settings.DEFAULT_FILE_STORAGE.endswith("S3Boto3Storage"):
        from storages.backends.s3boto3 import S3Boto3Storage

        class S3Backend(LocalStorageBackend):
            storage = S3Boto3Storage()

        return S3Backend()

    return LocalStorageBackend()


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
