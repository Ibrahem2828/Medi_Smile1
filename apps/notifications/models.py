import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.accounts.models import User
from apps.appointments.models import Appointment


class Notification(models.Model):
    """Notification model for appointment change requests."""
    
    NOTIFICATION_TYPE_CHOICES = (
        ('appointment_update_request', _('Appointment Update Request')),
        ('appointment_cancel_request', _('Appointment Cancel Request')),
        ('appointment_confirmed', _('Appointment Confirmed')),
        ('appointment_cancelled', _('Appointment Cancelled')),
        ('appointment_completed', _('Appointment Completed')),
    )
    
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('rejected', _('Rejected')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_notifications',
        verbose_name=_('Sender')
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_notifications',
        verbose_name=_('Recipient')
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        verbose_name=_('Notification Type')
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Appointment'),
        null=True,
        blank=True
    )
    title = models.CharField(max_length=200, verbose_name=_('Title'))
    message = models.TextField(verbose_name=_('Message'))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    response_message = models.TextField(blank=True, null=True, verbose_name=_('Response Message'))
    # For update requests, store the proposed changes
    proposed_changes = models.JSONField(blank=True, null=True, verbose_name=_('Proposed Changes'))
    is_read = models.BooleanField(default=False, verbose_name=_('Is Read'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        db_table = 'notifications'
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"



















