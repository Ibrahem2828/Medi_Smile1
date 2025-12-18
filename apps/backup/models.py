import uuid
import os
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Backup(models.Model):
    """نموذج لحفظ معلومات النسخ الاحتياطي"""
    
    BACKUP_TYPE_CHOICES = (
        ('database', _('Database')),
        ('files', _('Files')),
        ('full', _('Full Backup (Database + Files)')),
    )
    
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    backup_type = models.CharField(
        max_length=20,
        choices=BACKUP_TYPE_CHOICES,
        verbose_name=_('Backup Type')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    
    # مسارات الملفات
    database_backup_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Database Backup Path')
    )
    files_backup_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Files Backup Path')
    )
    
    # معلومات الحجم
    database_size = models.BigIntegerField(
        default=0,
        verbose_name=_('Database Size (bytes)')
    )
    files_size = models.BigIntegerField(
        default=0,
        verbose_name=_('Files Size (bytes)')
    )
    total_size = models.BigIntegerField(
        default=0,
        verbose_name=_('Total Size (bytes)')
    )
    
    # معلومات إضافية
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Description')
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Error Message')
    )
    
    # معلومات التخزين
    storage_type = models.CharField(
        max_length=20,
        default='local',
        choices=(
            ('local', _('Local Storage')),
            ('s3', _('S3 Storage')),
        ),
        verbose_name=_('Storage Type')
    )
    storage_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Storage Path')
    )
    
    # الطوابع الزمنية
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    started_at = models.DateTimeField(blank=True, null=True, verbose_name=_('Started At'))
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name=_('Completed At'))
    
    class Meta:
        db_table = 'backups'
        verbose_name = _('Backup')
        verbose_name_plural = _('Backups')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['backup_type']),
        ]
    
    def __str__(self):
        return f"{self.get_backup_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duration(self):
        """حساب مدة النسخ الاحتياطي"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_completed(self):
        """التحقق من اكتمال النسخ الاحتياطي"""
        return self.status == 'completed'
    
    @property
    def is_failed(self):
        """التحقق من فشل النسخ الاحتياطي"""
        return self.status == 'failed'
    
    def delete(self, *args, **kwargs):
        """حذف الملفات المرتبطة عند حذف السجل"""
        if self.database_backup_path and os.path.exists(self.database_backup_path):
            try:
                os.remove(self.database_backup_path)
            except Exception:
                pass
        
        if self.files_backup_path and os.path.exists(self.files_backup_path):
            try:
                os.remove(self.files_backup_path)
            except Exception:
                pass
        
        super().delete(*args, **kwargs)














