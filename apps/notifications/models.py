import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from apps.accounts.models import User
from apps.appointments.models import Appointment


class Notification(models.Model):
    """
    Central notification model for MediSmile.

    Supports:
    - Appointments
    - Cases
    - Sessions
    - Community content
    - System / IT events
    """

    # ============================================================
    # Notification Type (What happened)
    # ============================================================

    NOTIFICATION_TYPE_CHOICES = (
        # --- Appointments ---
        ('appointment_update_request', _('Appointment Update Request')),
        ('appointment_cancel_request', _('Appointment Cancel Request')),
        ('appointment_confirmed', _('Appointment Confirmed')),
        ('appointment_cancelled', _('Appointment Cancelled')),
        ('appointment_completed', _('Appointment Completed')),

        # --- Community Content ---
        ('content_approval_request', _('Content Approval Request')),
        ('content_approved', _('Content Approved')),
        ('content_rejected', _('Content Rejected')),

        # --- Case & Sessions ---
        ('case_created', _('Case Created')),
        ('case_assigned', _('Case Assigned')),
        ('case_status_changed', _('Case Status Changed')),

        ('session_created', _('Session Created')),
        ('session_needs_review', _('Session Needs Review')),
        ('session_reviewed', _('Session Reviewed')),

        # --- Messaging ---
        ('new_message', _('New Message')),

        # --- System / IT ---
        ('system_alert', _('System Alert')),
        ('security_event', _('Security Event')),
    )

    # ============================================================
    # Notification Status (Actionable workflow)
    # ============================================================

    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('rejected', _('Rejected')),
        ('info', _('Informational')),
    )

    # ============================================================
    # Notification Priority (Visual & escalation)
    # ============================================================

    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        NORMAL = 'normal', _('Normal')
        HIGH = 'high', _('High')
        CRITICAL = 'critical', _('Critical')

    # ============================================================
    # Core Fields
    # ============================================================

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name=_('Sender'),
        help_text=_('User who triggered the notification (can be null for system events).')
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

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
        verbose_name=_('Priority')
    )

    # ============================================================
    # Direct Relations (kept for backward compatibility)
    # ============================================================

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Appointment'),
        null=True,
        blank=True
    )

    content = models.ForeignKey(
        'community.Content',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Content'),
        null=True,
        blank=True
    )

    # ============================================================
    # Generic Target (Case / Session / Message / Any future entity)
    # ============================================================

    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Target Content Type')
    )

    target_object_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_('Target Object ID')
    )

    target_object = GenericForeignKey(
        'target_content_type',
        'target_object_id'
    )

    # ============================================================
    # Display Content
    # ============================================================

    title = models.CharField(max_length=200, verbose_name=_('Title'))
    message = models.TextField(verbose_name=_('Message'))

    # ============================================================
    # Action / Response (for approvals & decisions)
    # ============================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='info',
        verbose_name=_('Status')
    )

    response_message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Response Message')
    )

    proposed_changes = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('Proposed Changes'),
        help_text=_('Used for update requests or approvals.')
    )

    # ============================================================
    # Read / Audit
    # ============================================================

    is_read = models.BooleanField(
        default=False,
        verbose_name=_('Is Read')
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Read At')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    # ============================================================
    # Meta
    # ============================================================

    class Meta:
        db_table = 'notifications'
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['is_read']),
            models.Index(fields=['created_at']),
        ]

    # ============================================================
    # String
    # ============================================================

    def __str__(self):
        return f"{self.title} → {self.recipient.email}"
