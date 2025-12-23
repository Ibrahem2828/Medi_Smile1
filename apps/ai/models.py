# apps/ai/models.py

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.cases.models import Case


class DiagnosisStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    COMPLETED = "completed", _("Completed")
    REVIEWED = "reviewed", _("Reviewed by Supervisor")


class ConfidenceLevel(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")


class UrgencyLevel(models.TextChoices):
    NON_URGENT = "non_urgent", _("Non Urgent")
    URGENT = "urgent", _("Urgent")


class SeverityLevel(models.TextChoices):
    LOW = "low", _("Low")
    MODERATE = "moderate", _("Moderate")
    HIGH = "high", _("High")


class AIDiagnosis(models.Model):
    """
    AI-powered initial dental triage based on patient symptoms.
    This model stores AI outputs, NOT a final medical diagnosis.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # =====================================================
    # Context
    # =====================================================
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="ai_diagnoses",
        verbose_name=_("Case"),
        help_text=_("Clinical case related to this AI analysis"),
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ai_diagnoses",
        limit_choices_to={"role__name": "patient"},
        verbose_name=_("Patient"),
    )

    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_ai_diagnoses",
        verbose_name=_("Requested By"),
        help_text=_("User who initiated the AI analysis"),
    )

    # =====================================================
    # Input
    # =====================================================
    raw_symptoms = models.TextField(
        verbose_name=_("Raw Symptoms Input"),
        help_text=_("Original text after speech-to-text or manual input"),
    )

    normalized_symptoms = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Normalized Symptoms"),
        help_text=_("Cleaned and normalized Arabic text"),
    )

    # =====================================================
    # AI Output (Technical)
    # =====================================================
    diagnosis_label = models.CharField(
        max_length=255,
        verbose_name=_("Diagnosis Label"),
        help_text=_("Internal diagnosis identifier (technical)"),
    )

    confidence_level = models.CharField(
        max_length=20,
        choices=ConfidenceLevel.choices,
        default=ConfidenceLevel.MEDIUM,
        verbose_name=_("Confidence Level"),
    )

    severity_level = models.CharField(
        max_length=20,
        choices=SeverityLevel.choices,
        verbose_name=_("Severity Level"),
    )

    urgency_level = models.CharField(
        max_length=20,
        choices=UrgencyLevel.choices,
        verbose_name=_("Urgency Level"),
    )

    ai_metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("AI Metadata"),
        help_text=_(
            "Technical AI output (rules fired, similarity scores, alternatives)"
        ),
    )

    # =====================================================
    # Patient Explanation
    # =====================================================
    patient_explanation = models.TextField(
        verbose_name=_("Patient Explanation"),
        help_text=_("Safe, non-alarming explanation shown to the patient"),
    )

    recommendations = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Recommendations"),
        help_text=_("General advice and next steps"),
    )

    # =====================================================
    # Lifecycle
    # =====================================================
    status = models.CharField(
        max_length=20,
        choices=DiagnosisStatus.choices,
        default=DiagnosisStatus.PENDING,
        verbose_name=_("Status"),
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_ai_diagnoses",
        verbose_name=_("Reviewed By"),
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Reviewed At"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    class Meta:
        db_table = "ai_diagnoses"
        verbose_name = _("AI Diagnosis")
        verbose_name_plural = _("AI Diagnoses")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient"]),
            models.Index(fields=["case"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"AI Diagnosis - {self.patient.email} ({self.created_at.date()})"
