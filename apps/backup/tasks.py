from celery import shared_task
import logging

from apps.backup.engine import BackupEngine

from .models import Backup
from .services import mark_backup_completed, mark_backup_failed

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={"max_retries": 3})
def run_backup_task(self, backup_id: str):
    backup = Backup.objects.get(id=backup_id)
    engine = BackupEngine()

    try:
        if backup.backup_type in {"database", "full"}:
            engine.backup_database(backup)

        if backup.backup_type in {"files", "full"}:
            engine.backup_files(backup)

        backup.total_size = (backup.database_size or 0) + (backup.files_size or 0)
        mark_backup_completed(backup)

        return {"success": True, "backup_id": str(backup.id)}

    except Exception as exc:
        logger.exception("Backup failed")
        mark_backup_failed(backup, str(exc))
        raise
