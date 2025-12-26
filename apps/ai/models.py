# apps/ai/models.py
import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DiagnosisStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    REVIEWED = "reviewed", _("Reviewed by Supervisor")


class ConfidenceLevel(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")


class SeverityLevel(models.TextChoices):
    LOW = "low", _("Low")
    MODERATE = "moderate", _("Moderate")
    HIGH = "high", _("High")


class UrgencyLevel(models.TextChoices):
    NON_URGENT = "non_urgent", _("Non Urgent")
    URGENT = "urgent", _("Urgent")


class AIDiagnosis(models.Model):
    """
    AI-powered initial dental assessment.

    Notes:
    - NOT a final medical diagnosis.
    - AI inference is executed in external AI Engine (FastAPI).
    - Stored data is auditable and immutable by design.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Context
    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="ai_diagnoses",
        verbose_name=_("Case"),
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_diagnoses",
        limit_choices_to={"role__name": "patient"},
        verbose_name=_("Patient"),
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_ai_diagnoses",
        verbose_name=_("Requested By"),
    )

    # Input
    raw_symptoms = models.TextField(verbose_name=_("Raw Symptoms Input"))
    normalized_symptoms = models.TextField(
        null=True, blank=True, verbose_name=_("Normalized Symptoms")
    )

    # Output (headline + findings)
    diagnosis_label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Diagnosis Label"),
        help_text=_("Internal label returned by engine/fusion (technical)"),
    )
    primary_diagnosis = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Primary Diagnosis"),
    )
    detected_findings = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Detected Findings"),
        help_text=_("Structured list of findings (JSON)"),
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
        default=SeverityLevel.MODERATE,
        verbose_name=_("Severity Level"),
    )
    urgency_level = models.CharField(
        max_length=20,
        choices=UrgencyLevel.choices,
        default=UrgencyLevel.NON_URGENT,
        verbose_name=_("Urgency Level"),
    )

    ai_metadata = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("AI Metadata"),
        help_text=_("Technical output payload from engine (kept for audit/debug)"),
    )

    # Patient-safe output
    patient_explanation = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Patient Explanation"),
    )
    report_text = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Detailed Report Text"),
    )
    recommendations = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Recommendations"),
    )

    # Lifecycle
    status = models.CharField(
        max_length=20,
        choices=DiagnosisStatus.choices,
        default=DiagnosisStatus.PENDING,
        verbose_name=_("Status"),
    )
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Error Message"),
        help_text=_("Set when engine fails"),
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_ai_diagnoses",
        verbose_name=_("Reviewed By"),
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Reviewed At"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

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

    def __str__(self) -> str:
        headline = self.primary_diagnosis or self.diagnosis_label or "AI Diagnosis"
        return f"{headline} | patient={self.patient_id} | case={self.case_id} | {self.status}"
