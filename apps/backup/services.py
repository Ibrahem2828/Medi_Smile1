import logging
from typing import Optional

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.services import log_audit_event
from apps.backup.engine import BackupEngine, BackupIntegrityError
from apps.notifications.services import notify_user
from .models import Backup

logger = logging.getLogger(__name__)


def _role_name(user) -> Optional[str]:
    return getattr(getattr(user, "role", None), "name", None)


# ============================================================
# Core Backup Services
# ============================================================
def create_backup(
    *,
    actor,
    backup_type: str,
    description: Optional[str] = None,
    trigger_source=Backup.TriggerSource.MANUAL,
) -> Backup:
    role_name = _role_name(actor)
    if role_name != Role.TECH_SUPPORT and not getattr(actor, "is_superuser", False):
        raise PermissionDenied("Only Tech Support can create backups.")

    engine = BackupEngine()

    backup = Backup.objects.create(
        backup_type=backup_type,
        status=Backup.Status.IN_PROGRESS,
        started_at=timezone.now(),
        created_by=actor,
        trigger_source=trigger_source,
        description=description,
        storage_type=engine.storage_type,
        storage_path=engine.backup_directory,
    )

    log_audit_event(
        user=actor,
        action="backup.created",
        description="Backup process started",
        content_object=backup,
        metadata={"backup_type": backup_type},
    )

    return backup


def mark_backup_completed(backup: Backup):
    # Do not create a successful audit trail unless every requested artifact
    # exists and has already passed the engine's integrity checks.
    engine = BackupEngine()
    if backup.backup_type in {Backup.BackupType.DATABASE, Backup.BackupType.FULL}:
        if not backup.database_backup_path:
            raise BackupIntegrityError("Database backup artifact is missing.")
        engine.verify_database_backup(backup.database_backup_path)
    if backup.backup_type in {Backup.BackupType.FILES, Backup.BackupType.FULL}:
        if not backup.files_backup_path:
            raise BackupIntegrityError("Files backup artifact is missing.")
        engine.verify_files_backup(backup.files_backup_path)
    backup.status = Backup.Status.COMPLETED
    backup.completed_at = timezone.now()
    backup.save()

    log_audit_event(
        user=backup.created_by,
        action="backup.completed",
        description="Backup completed successfully",
        content_object=backup,
    )


def mark_backup_failed(backup: Backup, error: str):
    backup.status = Backup.Status.FAILED
    backup.error_message = error
    backup.completed_at = timezone.now()
    backup.save()

    log_audit_event(
        user=backup.created_by,
        action="backup.failed",
        description="Backup failed",
        content_object=backup,
        metadata={"error": error},
    )

    if backup.created_by:
        try:
            notify_user(
                user=backup.created_by,
                title="Backup Failed",
                message=f"Backup {backup.id} failed. Error: {error}",
                data={
                    "backup_id": str(backup.id),
                    "backup_type": backup.backup_type,
                },
            )
        except Exception:
            logger.exception("Failed to send backup failure notification")


def restore_backup(*, actor, backup: Backup, restore_type: str):
    role_name = _role_name(actor)
    if role_name != Role.TECH_SUPPORT and not getattr(actor, "is_superuser", False):
        raise PermissionDenied("Only Tech Support can restore backups.")

    engine = BackupEngine()

    if backup.status != Backup.Status.COMPLETED:
        raise BackupIntegrityError("Only a completed, verified backup can be restored.")

    log_audit_event(
        user=actor,
        action="backup.restore.started",
        description="Backup restore started",
        content_object=backup,
        metadata={"restore_type": restore_type},
    )

    try:
        if restore_type in {"database", "full"}:
            if not backup.database_backup_path:
                raise BackupIntegrityError("Backup does not contain a database artifact.")
            engine.restore_database(backup.database_backup_path)

        if restore_type in {"files", "full"}:
            if not backup.files_backup_path:
                raise BackupIntegrityError("Backup does not contain a files artifact.")
            engine.restore_files(backup.files_backup_path)
    except Exception as exc:
        log_audit_event(
            user=actor,
            action="backup.restore.failed",
            description="Backup restore failed",
            content_object=backup,
            metadata={"restore_type": restore_type, "error": str(exc)},
        )
        raise

    log_audit_event(
        user=actor,
        action="backup.restore.completed",
        description="Backup restored successfully",
        content_object=backup,
    )
