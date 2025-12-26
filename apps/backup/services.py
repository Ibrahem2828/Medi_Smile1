import logging
from typing import Optional

from apps.notifications.services import notify_user
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from apps.audit.services import log_audit_event
from apps.accounts.models import Role
from .models import Backup
from apps.backup.engine import BackupEngine


logger = logging.getLogger(__name__)


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
    if actor.role.name != Role.TECH_SUPPORT:
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

    # 🔔 Notify Tech Support
    notify_user(
        user=backup.created_by,
        title="Backup Failed",
        message=f"Backup {backup.id} failed. Error: {error}",
        data={
            "backup_id": str(backup.id),
            "backup_type": backup.backup_type,
        },
    )


def restore_backup(*, actor, backup: Backup, restore_type: str):
    if actor.role.name != Role.TECH_SUPPORT:
        raise PermissionDenied

    engine = BackupEngine()

    log_audit_event(
        user=actor,
        action="backup.restore.started",
        description="Backup restore started",
        content_object=backup,
        metadata={"restore_type": restore_type},
    )

    if restore_type in {"database", "full"}:
        engine.restore_database(backup.database_backup_path)

    if restore_type in {"files", "full"}:
        engine.restore_files(backup.files_backup_path)

    log_audit_event(
        user=actor,
        action="backup.restore.completed",
        description="Backup restored successfully",
        content_object=backup,
    )
