from celery import shared_task
from django.utils import timezone
from .services import BackupService, create_monthly_backup
from .models import Backup
import logging

logger = logging.getLogger(__name__)


# ============================================================
# Monthly Backup Task
# ============================================================

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={'max_retries': 3})
def monthly_backup_task(self):
    """
    مهمة النسخ الاحتياطي الشهري (تلقائية)
    - Full Backup (Database + Files)
    - قابلة لإعادة المحاولة عند الفشل
    """
    logger.info("🗓️ Starting monthly backup task")

    try:
        backup = create_monthly_backup()

        if backup.is_completed:
            logger.info(f"✅ Monthly backup completed successfully | ID={backup.id}")
            return {
                'success': True,
                'backup_id': str(backup.id),
                'status': backup.status,
                'completed_at': backup.completed_at.isoformat() if backup.completed_at else None,
            }

        logger.error(f"❌ Monthly backup failed | ID={backup.id} | Error={backup.error_message}")
        return {
            'success': False,
            'backup_id': str(backup.id),
            'status': backup.status,
            'error': backup.error_message,
        }

    except Exception as exc:
        logger.exception("🔥 Monthly backup task crashed")
        raise self.retry(exc=exc)


# ============================================================
# Cleanup Old Backups Task
# ============================================================

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=30, retry_kwargs={'max_retries': 3})
def cleanup_old_backups_task(self, days_to_keep=30):
    """
    مهمة تنظيف النسخ الاحتياطية القديمة
    - تحذف النسخ المكتملة فقط
    - افتراضيًا أقدم من 30 يوم
    """
    logger.info(f"🧹 Starting cleanup task | days_to_keep={days_to_keep}")

    try:
        service = BackupService()
        result = service.cleanup_old_backups(days_to_keep=days_to_keep)

        if result.get('success'):
            logger.info(f"✅ Cleanup completed | deleted={result.get('deleted_count', 0)}")
        else:
            logger.warning(f"⚠️ Cleanup completed with warnings | {result}")

        return result

    except Exception as exc:
        logger.exception("🔥 Cleanup task crashed")
        raise self.retry(exc=exc)


# ============================================================
# On-demand Backup Task
# ============================================================

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={'max_retries': 2})
def create_backup_task(self, backup_type='full', description=None):
    """
    مهمة إنشاء نسخة احتياطية عند الطلب
    - database | files | full
    - يتم استدعاؤها من API
    """
    logger.info(f"🚀 Starting backup task | type={backup_type}")

    service = BackupService()

    try:
        # ----------------------------------------------------
        # Database Backup
        # ----------------------------------------------------
        if backup_type == 'database':
            backup = Backup.objects.create(
                backup_type='database',
                status='in_progress',
                started_at=timezone.now(),
                description=description,
                storage_type=service.storage_type,
                storage_path=service.backup_directory,
            )

            result = service.backup_database(backup)

            if result.get('success'):
                backup.status = 'completed'
                backup.completed_at = timezone.now()
            else:
                backup.status = 'failed'
                backup.error_message = result.get('error')

            backup.save()
            return {
                'success': backup.is_completed,
                'backup_id': str(backup.id),
                'status': backup.status,
            }

        # ----------------------------------------------------
        # Files Backup
        # ----------------------------------------------------
        if backup_type == 'files':
            backup = Backup.objects.create(
                backup_type='files',
                status='in_progress',
                started_at=timezone.now(),
                description=description,
                storage_type=service.storage_type,
                storage_path=service.backup_directory,
            )

            result = service.backup_files(backup)

            if result.get('success'):
                backup.status = 'completed'
                backup.completed_at = timezone.now()
            else:
                backup.status = 'failed'
                backup.error_message = result.get('error')

            backup.save()
            return {
                'success': backup.is_completed,
                'backup_id': str(backup.id),
                'status': backup.status,
            }

        # ----------------------------------------------------
        # Full Backup (Database + Files)
        # ----------------------------------------------------
        backup = service.create_full_backup(description=description)

        return {
            'success': backup.is_completed,
            'backup_id': str(backup.id),
            'status': backup.status,
        }

    except Exception as exc:
        logger.exception("🔥 Create backup task crashed")
        raise self.retry(exc=exc)
