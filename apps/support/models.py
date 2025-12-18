import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class SupportTicket(models.Model):
    """Support ticket model for technical support requests."""
    
    CATEGORY_CHOICES = (
        ('technical', _('Technical Problem')),
        ('account', _('Account Issue')),
        ('feature', _('Feature Request')),
        ('bug', _('Bug Report')),
        ('other', _('Other')),
    )
    
    PRIORITY_CHOICES = (
        ('urgent', _('Urgent')),
        ('medium', _('Medium')),
        ('low', _('Low')),
    )
    
    STATUS_CHOICES = (
        ('open', _('Open')),
        ('in_progress', _('In Progress')),
        ('resolved', _('Resolved')),
        ('closed', _('Closed')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='support_tickets',
        verbose_name=_('User')
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='technical',
        verbose_name=_('Category')
    )
    subject = models.CharField(max_length=200, verbose_name=_('Subject'))
    message = models.TextField(verbose_name=_('Message'))
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_('Priority')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name=_('Status')
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        limit_choices_to={'role': 'tech_support'},
        verbose_name=_('Assigned To')
    )
    resolution = models.TextField(blank=True, null=True, verbose_name=_('Resolution'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Resolved At'))
    
    class Meta:
        db_table = 'support_tickets'
        verbose_name = _('Support Ticket')
        verbose_name_plural = _('Support Tickets')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject} - {self.user.email}"


class SupportTicketResponse(models.Model):
    """Response model for support ticket conversations."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name=_('Ticket')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ticket_responses',
        verbose_name=_('User')
    )
    message = models.TextField(verbose_name=_('Message'))
    is_internal = models.BooleanField(
        default=False,
        verbose_name=_('Is Internal'),
        help_text=_('If true, this response is only visible to tech support staff')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        db_table = 'support_ticket_responses'
        verbose_name = _('Support Ticket Response')
        verbose_name_plural = _('Support Ticket Responses')
        ordering = ['created_at']
    
    def __str__(self):
        return f"Response to {self.ticket.subject} by {self.user.email}"

