from celery import shared_task
from celery.schedules import crontab
from django.utils import timezone
from .services import BackupService, create_monthly_backup
from .models import Backup
import logging

logger = logging.getLogger(__name__)


@shared_task
def monthly_backup_task():
    """مهمة النسخ الاحتياطي الشهري"""
    try:
        logger.info("Starting monthly backup task...")
        backup = create_monthly_backup()
        
        if backup.is_completed:
            logger.info(f"Monthly backup completed successfully: {backup.id}")
            return {
                'success': True,
                'backup_id': str(backup.id),
                'message': 'Monthly backup completed successfully'
            }
        else:
            logger.error(f"Monthly backup failed: {backup.error_message}")
            return {
                'success': False,
                'backup_id': str(backup.id),
                'error': backup.error_message
            }
    except Exception as e:
        logger.error(f"Monthly backup task error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_old_backups_task(days_to_keep=30):
    """مهمة تنظيف النسخ الاحتياطية القديمة"""
    try:
        service = BackupService()
        result = service.cleanup_old_backups(days_to_keep=days_to_keep)
        logger.info(f"Cleanup task completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Cleanup task error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def create_backup_task(backup_type='full', description=None):
    """مهمة لإنشاء نسخة احتياطية حسب الطلب"""
    try:
        service = BackupService()
        
        if backup_type == 'database':
            backup = Backup.objects.create(
                backup_type='database',
                status='in_progress',
                started_at=timezone.now(),
                description=description
            )
            result = service.backup_database(backup)
            if result['success']:
                backup.status = 'completed'
                backup.completed_at = timezone.now()
                backup.save()
            return backup
        
        elif backup_type == 'files':
            backup = Backup.objects.create(
                backup_type='files',
                status='in_progress',
                started_at=timezone.now(),
                description=description
            )
            result = service.backup_files(backup)
            if result['success']:
                backup.status = 'completed'
                backup.completed_at = timezone.now()
                backup.save()
            return backup
        
        else:  # full
            backup = service.create_full_backup(description=description)
            return backup
            
    except Exception as e:
        logger.error(f"Create backup task error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }














