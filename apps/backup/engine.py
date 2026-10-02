"""Verified database and private-file backup primitives.

The engine intentionally supports only real PostgreSQL and SQLite backups. It
never writes placeholder content and it refuses destructive restores unless an
explicit, separate recovery target is configured.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.db import connections
from django.utils import timezone


class BackupIntegrityError(RuntimeError):
    """A backup artifact cannot be verified or restored safely."""


class BackupEngine:
    """Low-level executor. Permissions and audit events belong in services."""

    def __init__(self):
        self.storage_type = settings.BACKUP_STORAGE_TYPE
        if self.storage_type != "local":
            # Do not claim a remote backup succeeded while its artifacts are
            # actually written to local disk.  A real S3/immutable-backup
            # adapter must be configured before enabling that storage mode.
            raise BackupIntegrityError(
                f"Unsupported backup storage type: {self.storage_type}. Configure a verified adapter."
            )
        root = Path(settings.BACKUP_DIRECTORY).resolve()
        self.backup_directory = root / timezone.now().strftime("%Y/%m/%d")
        self.backup_directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _database_engine(self) -> str:
        return connections["default"].settings_dict["ENGINE"]

    def _run(self, command: list[str], *, env: dict[str, str] | None = None) -> None:
        try:
            subprocess.run(
                command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=env,
            )
        except FileNotFoundError as exc:
            raise BackupIntegrityError(
                f"Required backup executable is not installed: {command[0]}"
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "backup command failed").strip()
            raise BackupIntegrityError(detail[-1000:]) from exc

    @staticmethod
    def _postgres_environment(config: dict) -> dict[str, str]:
        environment = os.environ.copy()
        if config.get("PASSWORD"):
            environment["PGPASSWORD"] = str(config["PASSWORD"])
        return environment

    # ============================
    # Database
    # ============================
    def backup_database(self, backup):
        engine = self._database_engine()
        if engine == "django.db.backends.sqlite3":
            path = self.backup_directory / f"db_{backup.id}.sqlite3"
            connections["default"].ensure_connection()
            source = connections["default"].connection
            with sqlite3.connect(path) as destination:
                source.backup(destination)
        elif engine == "django.db.backends.postgresql":
            config = connections["default"].settings_dict
            path = self.backup_directory / f"db_{backup.id}.dump"
            command = [
                os.getenv("PG_DUMP_PATH", "pg_dump"), "--format=custom", "--no-owner",
                "--file", str(path), "--host", str(config.get("HOST") or "localhost"),
                "--port", str(config.get("PORT") or "5432"),
                "--username", str(config.get("USER") or ""), str(config.get("NAME") or ""),
            ]
            self._run(command, env=self._postgres_environment(config))
        else:
            raise BackupIntegrityError(f"Database engine is not supported for backup: {engine}")

        self.verify_database_backup(path)
        backup.database_backup_path = str(path)
        backup.database_size = path.stat().st_size
        backup.save(update_fields=["database_backup_path", "database_size"])

    def verify_database_backup(self, path: str | Path) -> None:
        artifact = Path(path)
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise BackupIntegrityError("Database backup artifact is missing or empty.")
        if artifact.suffix == ".sqlite3":
            try:
                with sqlite3.connect(f"file:{artifact.as_posix()}?mode=ro", uri=True) as connection:
                    result = connection.execute("PRAGMA integrity_check").fetchone()
            except sqlite3.Error as exc:
                raise BackupIntegrityError("SQLite backup integrity check failed.") from exc
            if not result or result[0].lower() != "ok":
                raise BackupIntegrityError("SQLite backup integrity check did not return ok.")
        elif artifact.suffix == ".dump":
            self._run([os.getenv("PG_RESTORE_PATH", "pg_restore"), "--list", str(artifact)])
        else:
            raise BackupIntegrityError("Unknown database backup format.")

    def _restore_sqlite_database(self, source_path: Path, target_url: str) -> None:
        parsed = urlparse(target_url)
        if parsed.scheme != "sqlite":
            raise BackupIntegrityError("SQLite restore requires a sqlite:/// recovery database URL.")
        target_path = Path(unquote(parsed.path)).resolve()
        if target_path == source_path.resolve():
            raise BackupIntegrityError("Restore target must be separate from the backup artifact.")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(source_path) as source, sqlite3.connect(target_path) as destination:
            source.backup(destination)
        self.verify_database_backup(target_path)

    def _restore_postgres_database(self, source_path: Path, target_url: str) -> None:
        parsed = urlparse(target_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise BackupIntegrityError("PostgreSQL restore requires a postgresql:// recovery database URL.")
        if not parsed.path or parsed.path == "/":
            raise BackupIntegrityError("Recovery database name is required.")
        if target_url == getattr(settings, "DATABASE_URL", ""):
            raise BackupIntegrityError("Restore target must not be the running production database.")
        environment = os.environ.copy()
        if parsed.password:
            environment["PGPASSWORD"] = unquote(parsed.password)
        self._run([
            os.getenv("PG_RESTORE_PATH", "pg_restore"), "--clean", "--if-exists",
            "--no-owner", "--dbname", target_url, str(source_path),
        ], env=environment)

    def restore_database(self, path: str):
        if not settings.BACKUP_RESTORE_ENABLED:
            raise BackupIntegrityError("Database restore is disabled. Configure an isolated recovery target first.")
        if not settings.BACKUP_RESTORE_DATABASE_URL:
            raise BackupIntegrityError("BACKUP_RESTORE_DATABASE_URL is required for restore.")
        artifact = Path(path)
        self.verify_database_backup(artifact)
        if artifact.suffix == ".sqlite3":
            self._restore_sqlite_database(artifact, settings.BACKUP_RESTORE_DATABASE_URL)
        elif artifact.suffix == ".dump":
            self._restore_postgres_database(artifact, settings.BACKUP_RESTORE_DATABASE_URL)
        else:  # pragma: no cover - guarded by verify_database_backup
            raise BackupIntegrityError("Unknown database backup format.")

    # ============================
    # Files
    # ============================
    @staticmethod
    def _archive_roots() -> list[tuple[str, Path]]:
        return [
            ("private", Path(settings.PRIVATE_MEDIA_ROOT)),
            ("media", Path(settings.MEDIA_ROOT)),
        ]

    def backup_files(self, backup):
        path = self.backup_directory / f"files_{backup.id}.zip"
        manifest: dict[str, dict[str, str | int]] = {}
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for prefix, root in self._archive_roots():
                if not root.exists():
                    continue
                for file_path in root.rglob("*"):
                    if not file_path.is_file() or file_path.is_symlink():
                        continue
                    relative = file_path.relative_to(root).as_posix()
                    archive_name = f"{prefix}/{relative}"
                    archive.write(file_path, archive_name)
                    manifest[archive_name] = {
                        "size": file_path.stat().st_size,
                        "sha256": self._sha256(file_path),
                    }
            archive.writestr("_manifest.json", json.dumps(manifest, sort_keys=True))

        self.verify_files_backup(path)
        backup.files_backup_path = str(path)
        backup.files_size = path.stat().st_size
        backup.save(update_fields=["files_backup_path", "files_size"])

    @staticmethod
    def _safe_archive_member(name: str) -> bool:
        member = Path(name)
        return (
            not member.is_absolute() and ".." not in member.parts
            and name.startswith(("private/", "media/"))
        )

    def verify_files_backup(self, path: str | Path) -> None:
        artifact = Path(path)
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise BackupIntegrityError("Files backup artifact is missing or empty.")
        try:
            with zipfile.ZipFile(artifact, "r") as archive:
                if archive.testzip() is not None:
                    raise BackupIntegrityError("Files backup contains a corrupt ZIP member.")
                try:
                    manifest = json.loads(archive.read("_manifest.json"))
                except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise BackupIntegrityError("Files backup manifest is missing or invalid.") from exc
                if not isinstance(manifest, dict):
                    raise BackupIntegrityError("Files backup manifest is invalid.")
                for name, details in manifest.items():
                    if not self._safe_archive_member(name) or not isinstance(details, dict):
                        raise BackupIntegrityError("Files backup contains an unsafe member path.")
                    payload = archive.read(name)
                    if len(payload) != details.get("size"):
                        raise BackupIntegrityError(f"Files backup size mismatch: {name}")
                    if hashlib.sha256(payload).hexdigest() != details.get("sha256"):
                        raise BackupIntegrityError(f"Files backup checksum mismatch: {name}")
        except zipfile.BadZipFile as exc:
            raise BackupIntegrityError("Files backup is not a valid ZIP archive.") from exc

    def restore_files(self, path: str):
        if not settings.BACKUP_RESTORE_ENABLED:
            raise BackupIntegrityError("Files restore is disabled. Configure an isolated recovery target first.")
        if not settings.BACKUP_RESTORE_MEDIA_ROOT:
            raise BackupIntegrityError("BACKUP_RESTORE_MEDIA_ROOT is required for restore.")
        artifact = Path(path)
        self.verify_files_backup(artifact)
        destination = Path(settings.BACKUP_RESTORE_MEDIA_ROOT).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(artifact, "r") as archive:
            manifest = json.loads(archive.read("_manifest.json"))
            for name in manifest:
                target = (destination / name).resolve()
                if destination not in target.parents:
                    raise BackupIntegrityError("Unsafe restore destination.")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, target.open("wb") as output:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(chunk)
