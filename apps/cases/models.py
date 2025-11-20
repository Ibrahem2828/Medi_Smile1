import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class Case(models.Model):
    """Medical case model."""
    
    STATUS_CHOICES = (
        ('open', _('Open')),
        ('assigned', _('Assigned')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    )
    
    PRIORITY_CHOICES = (
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name=_('Title'))
    description = models.TextField(verbose_name=_('Description'))
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='cases',
        limit_choices_to={'role': 'patient'},
        verbose_name=_('Patient')
    )
    student = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='assigned_cases',
        limit_choices_to={'role': 'student'},
        verbose_name=_('Assigned Student')
    )
    supervisor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='supervised_cases',
        limit_choices_to={'role': 'supervisor'},
        verbose_name=_('Supervisor')
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name=_('Status'))
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name=_('Priority'))
    is_public = models.BooleanField(default=False, verbose_name=_('Is Public'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        db_table = 'cases'
        verbose_name = _('Case')
        verbose_name_plural = _('Cases')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class CaseHistory(models.Model):
    """Case history model for tracking changes."""
    
    ACTION_CHOICES = (
        ('created', _('Created')),
        ('updated', _('Updated')),
        ('assigned', _('Assigned')),
        ('status_changed', _('Status Changed')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='history', verbose_name=_('Case'))
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name=_('Action'))
    description = models.TextField(verbose_name=_('Description'))
    performed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name=_('Performed By')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        db_table = 'case_history'
        verbose_name = _('Case History')
        verbose_name_plural = _('Case Histories')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.case.title} - {self.action}"


class CaseAssignmentRequest(models.Model):
    """Model for case assignment requests."""
    
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='assignment_requests', verbose_name=_('Case'))
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='assignment_requests',
        limit_choices_to={'role': 'student'},
        verbose_name=_('Student')
    )
    message = models.TextField(blank=True, null=True, verbose_name=_('Message'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_('Status'))
    supervisor_response = models.TextField(blank=True, null=True, verbose_name=_('Supervisor Response'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        db_table = 'case_assignment_requests'
        verbose_name = _('Case Assignment Request')
        verbose_name_plural = _('Case Assignment Requests')
        ordering = ['-created_at']
        unique_together = ['case', 'student']
    
    def __str__(self):
        return f"{self.case.title} - {self.student.username}"