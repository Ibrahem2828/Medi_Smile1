import uuid
import os
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from apps.accounts.models import User


class Backup(models.Model):
    """
    Backup Model

    Represents a single backup operation for the system.
    Supports database, files, or full backups with detailed
    lifecycle tracking and audit readiness.
    """

    # =====================================================
    # Backup Type
    # =====================================================
    class BackupType(models.TextChoices):
        DATABASE = 'database', _('Database')
        FILES = 'files', _('Files')
        FULL = 'full', _('Full Backup (Database + Files)')

    # =====================================================
    # Backup Status Lifecycle
    # =====================================================
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')

    # =====================================================
    # Backup Trigger
    # =====================================================
    class TriggerSource(models.TextChoices):
        MANUAL = 'manual', _('Manual')
        SCHEDULED = 'scheduled', _('Scheduled')
        SYSTEM = 'system', _('System')

    # =====================================================
    # Storage Type
    # =====================================================
    class StorageType(models.TextChoices):
        LOCAL = 'local', _('Local Storage')
        S3 = 's3', _('S3 Storage')

    # =====================================================
    # Core Fields
    # =====================================================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    backup_type = models.CharField(
        max_length=20,
        choices=BackupType.choices,
        verbose_name=_('Backup Type')
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('Status')
    )

    trigger_source = models.CharField(
        max_length=20,
        choices=TriggerSource.choices,
        default=TriggerSource.MANUAL,
        verbose_name=_('Triggered By')
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_backups',
        verbose_name=_('Created By'),
        help_text=_('User who initiated the backup')
    )

    # =====================================================
    # Backup Paths
    # =====================================================
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

    # =====================================================
    # Size Metadata
    # =====================================================
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

    # =====================================================
    # Storage Information
    # =====================================================
    storage_type = models.CharField(
        max_length=20,
        choices=StorageType.choices,
        default=StorageType.LOCAL,
        verbose_name=_('Storage Type')
    )

    storage_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Storage Root Path')
    )

    # =====================================================
    # Error & Notes
    # =====================================================
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Description / Notes')
    )

    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Error Message')
    )

    # =====================================================
    # Timestamps
    # =====================================================
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Started At')
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Completed At')
    )

    # =====================================================
    # Meta
    # =====================================================
    class Meta:
        db_table = 'backups'
        verbose_name = _('Backup')
        verbose_name_plural = _('Backups')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['backup_type']),
            models.Index(fields=['created_at']),
        ]

    # =====================================================
    # String Representation
    # =====================================================
    def __str__(self):
        return f"{self.get_backup_type_display()} | {self.created_at:%Y-%m-%d %H:%M}"

    # =====================================================
    # Computed Properties
    # =====================================================
    @property
    def duration(self):
        """Returns backup execution duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    @property
    def is_failed(self):
        return self.status == self.Status.FAILED

    # =====================================================
    # Safe Delete (Remove Files)
    # =====================================================
    def delete(self, *args, **kwargs):
        """
        Safely delete backup files from storage
        before removing database record.
        """
        for path in [self.database_backup_path, self.files_backup_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        super().delete(*args, **kwargs)
