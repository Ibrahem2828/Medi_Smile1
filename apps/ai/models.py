import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User
from apps.cases.models import Case


class AIDiagnosis(models.Model):
    """AI diagnosis model."""
    
    CONFIDENCE_LEVEL_CHOICES = (
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(
        Case, 
        on_delete=models.CASCADE, 
        related_name='ai_diagnoses',
        verbose_name=_('Case')
    )
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='ai_diagnoses',
        limit_choices_to={'role': 'patient'},
        verbose_name=_('Patient')
    )
    symptoms = models.TextField(verbose_name=_('Symptoms'))
    diagnosis = models.TextField(verbose_name=_('Diagnosis'))
    confidence_level = models.CharField(
        max_length=20, 
        choices=CONFIDENCE_LEVEL_CHOICES, 
        default='medium',
        verbose_name=_('Confidence Level')
    )
    recommendations = models.TextField(blank=True, null=True, verbose_name=_('Recommendations'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        db_table = 'ai_diagnoses'
        verbose_name = _('AI Diagnosis')
        verbose_name_plural = _('AI Diagnoses')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Diagnosis for {self.patient.username} - {self.case.title}"