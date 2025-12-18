import os
import subprocess
import tarfile
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from .models import Backup
import logging

logger = logging.getLogger(__name__)


class BackupService:
    """خدمة النسخ الاحتياطي"""
    
    def __init__(self, storage_type='local', backup_directory=None):
        self.storage_type = storage_type
        self.backup_directory = backup_directory or self._get_default_backup_directory()
        self._ensure_backup_directory()
    
    def _get_default_backup_directory(self):
        """الحصول على المجلد الافتراضي للنسخ الاحتياطي"""
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        return backup_dir
    
    def _ensure_backup_directory(self):
        """التأكد من وجود مجلد النسخ الاحتياطي"""
        os.makedirs(self.backup_directory, exist_ok=True)
        os.makedirs(os.path.join(self.backup_directory, 'database'), exist_ok=True)
        os.makedirs(os.path.join(self.backup_directory, 'files'), exist_ok=True)
    
    def backup_database(self, backup_instance=None):
        """إنشاء نسخة احتياطية لقاعدة البيانات"""
        try:
            db_settings = settings.DATABASES['default']
            db_name = db_settings['NAME']
            db_user = db_settings['USER']
            db_password = db_settings['PASSWORD']
            db_host = db_settings['HOST']
            db_port = db_settings['PORT']
            
            # إنشاء اسم الملف
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"db_backup_{timestamp}.dump"
            backup_path = os.path.join(self.backup_directory, 'database', backup_filename)
            
            # بناء أمر pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password
            
            pg_dump_cmd = [
                'pg_dump',
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-d', db_name,
                '-F', 'c',  # Custom format (compressed)
                '-f', backup_path,
            ]
            
            # تنفيذ النسخ الاحتياطي
            process = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            # الحصول على حجم الملف
            file_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
            
            if backup_instance:
                backup_instance.database_backup_path = backup_path
                backup_instance.database_size = file_size
                backup_instance.save()
            
            logger.info(f"Database backup completed: {backup_path}")
            return {
                'success': True,
                'path': backup_path,
                'size': file_size
            }
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Database backup failed: {e.stderr}"
            logger.error(error_msg)
            
            if backup_instance:
                backup_instance.error_message = error_msg
                backup_instance.status = 'failed'
                backup_instance.save()
            
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Database backup error: {str(e)}"
            logger.error(error_msg)
            
            if backup_instance:
                backup_instance.error_message = error_msg
                backup_instance.status = 'failed'
                backup_instance.save()
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def backup_files(self, backup_instance=None):
        """إنشاء نسخة احتياطية للملفات"""
        try:
            media_root = settings.MEDIA_ROOT
            
            if not os.path.exists(media_root):
                return {
                    'success': True,
                    'path': None,
                    'size': 0,
                    'message': 'Media directory does not exist'
                }
            
            # إنشاء اسم الملف
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"files_backup_{timestamp}.tar.gz"
            backup_path = os.path.join(self.backup_directory, 'files', backup_filename)
            
            # إنشاء ملف tar.gz
            total_size = 0
            with tarfile.open(backup_path, 'w:gz') as tar:
                for root, dirs, files in os.walk(media_root):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, media_root)
                        tar.add(file_path, arcname=arcname)
                        total_size += os.path.getsize(file_path)
            
            # الحصول على حجم الملف المضغوط
            compressed_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
            
            if backup_instance:
                backup_instance.files_backup_path = backup_path
                backup_instance.files_size = compressed_size
                backup_instance.save()
            
            logger.info(f"Files backup completed: {backup_path}")
            return {
                'success': True,
                'path': backup_path,
                'size': compressed_size,
                'original_size': total_size
            }
            
        except Exception as e:
            error_msg = f"Files backup error: {str(e)}"
            logger.error(error_msg)
            
            if backup_instance:
                backup_instance.error_message = error_msg
                backup_instance.status = 'failed'
                backup_instance.save()
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def create_full_backup(self, description=None):
        """إنشاء نسخة احتياطية كاملة (قاعدة البيانات + الملفات)"""
        backup = Backup.objects.create(
            backup_type='full',
            status='in_progress',
            started_at=timezone.now(),
            description=description,
            storage_type=self.storage_type,
            storage_path=self.backup_directory
        )
        
        try:
            # نسخ قاعدة البيانات
            db_result = self.backup_database(backup)
            if not db_result['success']:
                backup.status = 'failed'
                backup.error_message = db_result.get('error', 'Database backup failed')
                backup.save()
                return backup
            
            # نسخ الملفات
            files_result = self.backup_files(backup)
            if not files_result['success']:
                backup.status = 'failed'
                backup.error_message = files_result.get('error', 'Files backup failed')
                backup.save()
                return backup
            
            # تحديث المعلومات النهائية
            backup.total_size = backup.database_size + backup.files_size
            backup.status = 'completed'
            backup.completed_at = timezone.now()
            backup.save()
            
            logger.info(f"Full backup completed: {backup.id}")
            return backup
            
        except Exception as e:
            error_msg = f"Full backup error: {str(e)}"
            logger.error(error_msg)
            backup.status = 'failed'
            backup.error_message = error_msg
            backup.completed_at = timezone.now()
            backup.save()
            return backup
    
    def restore_database(self, backup_path):
        """استعادة قاعدة البيانات من نسخة احتياطية"""
        try:
            db_settings = settings.DATABASES['default']
            db_name = db_settings['NAME']
            db_user = db_settings['USER']
            db_password = db_settings['PASSWORD']
            db_host = db_settings['HOST']
            db_port = db_settings['PORT']
            
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password
            
            pg_restore_cmd = [
                'pg_restore',
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-d', db_name,
                '-c',  # Clean (drop) existing objects
                backup_path,
            ]
            
            process = subprocess.run(
                pg_restore_cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Database restored from: {backup_path}")
            return {
                'success': True,
                'message': 'Database restored successfully'
            }
            
        except Exception as e:
            error_msg = f"Database restore error: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def restore_files(self, backup_path, extract_to=None):
        """استعادة الملفات من نسخة احتياطية"""
        try:
            extract_to = extract_to or settings.MEDIA_ROOT
            
            # التأكد من وجود المجلد
            os.makedirs(extract_to, exist_ok=True)
            
            # استخراج الملفات
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(extract_to)
            
            logger.info(f"Files restored from: {backup_path}")
            return {
                'success': True,
                'message': 'Files restored successfully'
            }
            
        except Exception as e:
            error_msg = f"Files restore error: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def cleanup_old_backups(self, days_to_keep=30):
        """حذف النسخ الاحتياطية القديمة (أكثر من عدد محدد من الأيام)"""
        try:
            cutoff_date = timezone.now() - timezone.timedelta(days=days_to_keep)
            old_backups = Backup.objects.filter(
                created_at__lt=cutoff_date,
                status='completed'
            )
            
            deleted_count = 0
            for backup in old_backups:
                backup.delete()  # سيحذف الملفات تلقائيًا
                deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old backups")
            return {
                'success': True,
                'deleted_count': deleted_count
            }
            
        except Exception as e:
            error_msg = f"Cleanup error: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


def create_monthly_backup():
    """دالة لإنشاء نسخة احتياطية شهرية (يتم استدعاؤها من Celery)"""
    service = BackupService()
    backup = service.create_full_backup(description="Monthly automatic backup")
    return backup

