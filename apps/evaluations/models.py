import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User
from apps.appointments.models import Appointment


class Evaluation(models.Model):
    """Evaluation model based on ERD."""
    
    EVALUATOR_TYPE_CHOICES = (
        ('patient', _('Patient')),
        ('supervisor', _('Supervisor')),
        ('student', _('Student')),
        ('university', _('University')),
        ('admin', _('Admin Dashboard')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    patient = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_evaluations',
        limit_choices_to={'role': 'patient'},
        verbose_name=_('Patient'),
        db_column='patient_id',
        help_text=_('Patient who gave or received the evaluation')
    )
    student = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_evaluations',
        limit_choices_to={'role': 'student'},
        verbose_name=_('Student'),
        db_column='student_id',
        help_text=_('Student who participated in the service/appointment and was evaluated')
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evaluations',
        verbose_name=_('Appointment'),
        db_column='appointment_id',
        help_text=_('Appointment being evaluated')
    )
    rating = models.IntegerField(verbose_name=_('Rating'), help_text=_('Rating score (usually 1-5 or 1-10)'))
    comment = models.TextField(blank=True, null=True, verbose_name=_('Comment'), help_text=_('Evaluator comment about the service or performance'))
    evaluator_type = models.CharField(
        max_length=50,
        choices=EVALUATOR_TYPE_CHOICES,
        verbose_name=_('Evaluator Type'),
        help_text=_('Type of evaluator (Patient, Supervisor, Student, University, Admin Dashboard)')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        db_table = 'evaluations'
        verbose_name = _('Evaluation')
        verbose_name_plural = _('Evaluations')
        ordering = ['-created_at']
    
    def __str__(self):
        evaluator = self.get_evaluator_type_display()
        if self.student:
            return f"{evaluator} evaluation for student {self.student.username}"
        return f"{evaluator} evaluation - {self.rating} stars"