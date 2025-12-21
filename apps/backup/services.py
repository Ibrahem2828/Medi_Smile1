import os
import tarfile
import subprocess
import logging
from datetime import datetime
from typing import Optional, Dict

from django.conf import settings
from django.utils import timezone

from .models import Backup

logger = logging.getLogger(__name__)


# ============================================================
# Backup Service
# ============================================================

class BackupService:
    """
    Core service responsible for:
    - Database backups
    - Media files backups
    - Full backups
    - Restore operations
    - Cleanup jobs

    Designed to be used by:
    - API views
    - Celery tasks
    - Cron jobs
    """

    def __init__(
        self,
        storage_type: str = Backup.StorageType.LOCAL,
        backup_directory: Optional[str] = None,
    ):
        self.storage_type = storage_type
        self.backup_directory = backup_directory or self._default_backup_directory()
        self._ensure_directories()

    # --------------------------------------------------------
    # Directories
    # --------------------------------------------------------

    def _default_backup_directory(self) -> str:
        return os.path.join(settings.BASE_DIR, "backups")

    def _ensure_directories(self) -> None:
        os.makedirs(self.backup_directory, exist_ok=True)
        os.makedirs(os.path.join(self.backup_directory, "database"), exist_ok=True)
        os.makedirs(os.path.join(self.backup_directory, "files"), exist_ok=True)

    # --------------------------------------------------------
    # Database Backup
    # --------------------------------------------------------

    def backup_database(self, backup: Optional[Backup] = None) -> Dict:
        """
        Create PostgreSQL database backup using pg_dump.
        """
        try:
            db = settings.DATABASES["default"]

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"db_backup_{timestamp}.dump"
            path = os.path.join(self.backup_directory, "database", filename)

            env = os.environ.copy()
            env["PGPASSWORD"] = db.get("PASSWORD", "")

            command = [
                "pg_dump",
                "-h", db.get("HOST") or "localhost",
                "-p", str(db.get("PORT") or 5432),
                "-U", db.get("USER"),
                "-d", db.get("NAME"),
                "-F", "c",
                "-f", path,
            ]

            subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            size = os.path.getsize(path)

            if backup:
                backup.database_backup_path = path
                backup.database_size = size
                backup.save(update_fields=["database_backup_path", "database_size"])

            logger.info("Database backup completed: %s", path)
            return {"success": True, "path": path, "size": size}

        except subprocess.CalledProcessError as exc:
            error = f"Database backup failed: {exc.stderr}"
            logger.error(error)
            self._mark_failed(backup, error)
            return {"success": False, "error": error}

        except Exception as exc:
            error = f"Database backup error: {exc}"
            logger.exception(error)
            self._mark_failed(backup, error)
            return {"success": False, "error": error}

    # --------------------------------------------------------
    # Files Backup
    # --------------------------------------------------------

    def backup_files(self, backup: Optional[Backup] = None) -> Dict:
        """
        Create compressed tar.gz backup of MEDIA_ROOT.
        """
        try:
            media_root = settings.MEDIA_ROOT
            if not media_root or not os.path.exists(media_root):
                return {"success": True, "path": None, "size": 0}

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"files_backup_{timestamp}.tar.gz"
            path = os.path.join(self.backup_directory, "files", filename)

            total_original_size = 0

            with tarfile.open(path, "w:gz") as tar:
                for root, _, files in os.walk(media_root):
                    for file in files:
                        full_path = os.path.join(root, file)
                        arcname = os.path.relpath(full_path, media_root)
                        tar.add(full_path, arcname=arcname)
                        total_original_size += os.path.getsize(full_path)

            compressed_size = os.path.getsize(path)

            if backup:
                backup.files_backup_path = path
                backup.files_size = compressed_size
                backup.save(update_fields=["files_backup_path", "files_size"])

            logger.info("Files backup completed: %s", path)
            return {
                "success": True,
                "path": path,
                "size": compressed_size,
                "original_size": total_original_size,
            }

        except Exception as exc:
            error = f"Files backup error: {exc}"
            logger.exception(error)
            self._mark_failed(backup, error)
            return {"success": False, "error": error}

    # --------------------------------------------------------
    # Full Backup
    # --------------------------------------------------------

    def create_full_backup(
        self,
        *,
        created_by=None,
        trigger_source=Backup.TriggerSource.MANUAL,
        description: Optional[str] = None,
    ) -> Backup:
        """
        Execute full backup (database + files).
        """

        backup = Backup.objects.create(
            backup_type=Backup.BackupType.FULL,
            status=Backup.Status.IN_PROGRESS,
            started_at=timezone.now(),
            created_by=created_by,
            trigger_source=trigger_source,
            description=description,
            storage_type=self.storage_type,
            storage_path=self.backup_directory,
        )

        try:
            db_result = self.backup_database(backup)
            if not db_result["success"]:
                return backup

            files_result = self.backup_files(backup)
            if not files_result["success"]:
                return backup

            backup.total_size = backup.database_size + backup.files_size
            backup.status = Backup.Status.COMPLETED
            backup.completed_at = timezone.now()
            backup.save(update_fields=["total_size", "status", "completed_at"])

            logger.info("Full backup completed: %s", backup.id)
            return backup

        except Exception as exc:
            error = f"Full backup error: {exc}"
            logger.exception(error)
            self._mark_failed(backup, error)
            return backup

    # --------------------------------------------------------
    # Restore Operations
    # --------------------------------------------------------

    def restore_database(self, backup_path: str) -> Dict:
        try:
            db = settings.DATABASES["default"]

            env = os.environ.copy()
            env["PGPASSWORD"] = db.get("PASSWORD", "")

            command = [
                "pg_restore",
                "-h", db.get("HOST") or "localhost",
                "-p", str(db.get("PORT") or 5432),
                "-U", db.get("USER"),
                "-d", db.get("NAME"),
                "-c",
                backup_path,
            ]

            subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info("Database restored from %s", backup_path)
            return {"success": True}

        except Exception as exc:
            error = f"Database restore error: {exc}"
            logger.exception(error)
            return {"success": False, "error": error}

    def restore_files(self, backup_path: str, extract_to: Optional[str] = None) -> Dict:
        try:
            extract_to = extract_to or settings.MEDIA_ROOT
            os.makedirs(extract_to, exist_ok=True)

            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(extract_to)

            logger.info("Files restored from %s", backup_path)
            return {"success": True}

        except Exception as exc:
            error = f"Files restore error: {exc}"
            logger.exception(error)
            return {"success": False, "error": error}

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    def cleanup_old_backups(self, days_to_keep: int = 30) -> Dict:
        try:
            cutoff = timezone.now() - timezone.timedelta(days=days_to_keep)
            backups = Backup.objects.filter(
                created_at__lt=cutoff,
                status=Backup.Status.COMPLETED,
            )

            count = backups.count()
            for backup in backups:
                backup.delete()

            logger.info("Deleted %s old backups", count)
            return {"success": True, "deleted_count": count}

        except Exception as exc:
            error = f"Cleanup error: {exc}"
            logger.exception(error)
            return {"success": False, "error": error}

    # --------------------------------------------------------
    # Internal Helpers
    # --------------------------------------------------------

    def _mark_failed(self, backup: Optional[Backup], error: str) -> None:
        if not backup:
            return
        backup.status = Backup.Status.FAILED
        backup.error_message = error
        backup.completed_at = timezone.now()
        backup.save(
            update_fields=["status", "error_message", "completed_at"]
        )


# ============================================================
# Celery / Scheduler Entry Point
# ============================================================

def create_monthly_backup():
    """
    Monthly automatic backup (used by Celery / Cron).
    """
    service = BackupService()
    return service.create_full_backup(
        trigger_source=Backup.TriggerSource.SCHEDULED,
        description="Monthly automatic backup",
    )
