import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class Appointment(models.Model):
    """Appointment model based on ERD."""
    
    STATUS_CHOICES = (
        ('scheduled', _('Scheduled')),
        ('confirmed', _('Confirmed')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
        ('no_show', _('No Show')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='appointments',
        limit_choices_to={'role': 'patient'},
        verbose_name=_('Patient'),
        db_column='patient_id'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='user_appointments',
        verbose_name=_('User'),
        help_text=_('Usually the doctor or staff member managing the appointment'),
        db_column='user_id'
    )
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments',
        verbose_name=_('Case'),
        help_text=_('Related case (optional, for supervisor visibility)')
    )
    appointment_date = models.DateTimeField(verbose_name=_('Appointment Date'))
    status = models.CharField(
        max_length=50, 
        choices=STATUS_CHOICES, 
        default='scheduled',
        verbose_name=_('Status')
    )
    is_archived = models.BooleanField(default=False, verbose_name=_('Is Archived'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        db_table = 'appointments'
        verbose_name = _('Appointment')
        verbose_name_plural = _('Appointments')
        ordering = ['-appointment_date']
    
    def __str__(self):
        return f"Appointment {self.id} - {self.appointment_date.strftime('%Y-%m-%d %H:%M')}"