import uuid
import json
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.accounts.models import User


class AuditLog(models.Model):
    """Audit log model for tracking user activities."""
    
    ACTION_CHOICES = (
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('create', _('Create')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('view', _('View')),
        ('download', _('Download')),
        ('upload', _('Upload')),
        ('assign', _('Assign')),
        ('unassign', _('Unassign')),
        ('approve', _('Approve')),
        ('reject', _('Reject')),
        ('confirm', _('Confirm')),
        ('cancel', _('Cancel')),
        ('complete', _('Complete')),
        ('other', _('Other')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name=_('User')
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name=_('Action'))
    description = models.TextField(verbose_name=_('Description'))
    
    # Generic foreign key to track any model
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional data stored as JSON
    additional_data = models.JSONField(blank=True, null=True, verbose_name=_('Additional Data'))
    
    # Request information
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name=_('IP Address'))
    user_agent = models.TextField(blank=True, null=True, verbose_name=_('User Agent'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        db_table = 'audit_logs'
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} - {self.action} - {self.description[:50]}"