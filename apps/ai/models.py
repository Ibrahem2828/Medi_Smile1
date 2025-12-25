import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.cases.models import Case


# ============================================================
# ENUMS & CHOICES
# ============================================================

class DiagnosisStatus(models.TextChoices):
    """
    Lifecycle status of the AI diagnosis.
    """
    PENDING = "pending", _("Pending")
    COMPLETED = "completed", _("Completed")
    REVIEWED = "reviewed", _("Reviewed by Supervisor")


class ConfidenceLevel(models.TextChoices):
    """
    Confidence level of the AI-generated diagnosis.
    """
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")


class SeverityLevel(models.TextChoices):
    """
    Estimated clinical severity (educational, not medical).
    """
    LOW = "low", _("Low")
    MODERATE = "moderate", _("Moderate")
    HIGH = "high", _("High")


class UrgencyLevel(models.TextChoices):
    """
    Estimated urgency level for patient guidance.
    """
    NON_URGENT = "non_urgent", _("Non Urgent")
    URGENT = "urgent", _("Urgent")


# ============================================================
# MAIN MODEL
# ============================================================

class AIDiagnosis(models.Model):
    """
    AI-powered initial dental assessment.

    IMPORTANT:
    - This model DOES NOT represent a final medical diagnosis.
    - It stores an AI-generated triage result used for:
        * Patient guidance
        * Educational support
        * Case prioritization
    - All outputs are subject to academic and clinical supervision.
    """

    # =====================================================
    # Primary Key
    # =====================================================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # =====================================================
    # Context & Ownership
    # =====================================================
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="ai_diagnoses",
        verbose_name=_("Case"),
        help_text=_("Clinical case associated with this AI analysis"),
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ai_diagnoses",
        limit_choices_to={"role__name": "patient"},
        verbose_name=_("Patient"),
        help_text=_("Patient who owns this AI diagnosis"),
    )

    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_ai_diagnoses",
        verbose_name=_("Requested By"),
        help_text=_("User who initiated the AI diagnosis request"),
    )

    # =====================================================
    # INPUT DATA (FROM FRONTEND)
    # =====================================================
    raw_symptoms = models.TextField(
        verbose_name=_("Raw Symptoms Input"),
        help_text=_(
            "Original symptoms text received from the frontend "
            "(after speech-to-text or manual input)"
        ),
    )

    normalized_symptoms = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Normalized Symptoms"),
        help_text=_(
            "Cleaned and normalized Arabic text used internally by NLP models"
        ),
    )

    # =====================================================
    # AI OUTPUT (TECHNICAL & INTERNAL)
    # =====================================================

    # (existing field) Internal diagnosis identifier (keep)
    diagnosis_label = models.CharField(
        max_length=255,
        verbose_name=_("Diagnosis Label"),
        help_text=_(
            "Internal AI diagnosis identifier "
            "(used by decision policy and fusion model)"
        ),
    )

    # ✅ NEW: Primary headline diagnosis (patient-facing structured)
    primary_diagnosis = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Primary Diagnosis"),
        help_text=_(
            "Primary unified diagnosis headline (one main diagnosis). "
            "Used as the main title in patient report."
        ),
    )

    # ✅ NEW: All detected findings (multiple issues)
    detected_findings = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Detected Findings"),
        help_text=_(
            "Structured list of all detected problems/findings from AI, "
            "e.g. per-tooth findings + symptom findings. "
            "Stored as JSON and can be displayed in a structured UI."
        ),
    )

    confidence_level = models.CharField(
        max_length=20,
        choices=ConfidenceLevel.choices,
        default=ConfidenceLevel.MEDIUM,
        verbose_name=_("Confidence Level"),
        help_text=_("Overall confidence of the AI fusion result"),
    )

    severity_level = models.CharField(
        max_length=20,
        choices=SeverityLevel.choices,
        verbose_name=_("Severity Level"),
        help_text=_("Estimated severity level (educational only)"),
    )

    urgency_level = models.CharField(
        max_length=20,
        choices=UrgencyLevel.choices,
        verbose_name=_("Urgency Level"),
        help_text=_("Estimated urgency for patient guidance"),
    )

    ai_metadata = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("AI Metadata"),
        help_text=_(
            "Internal technical AI output (not exposed to patients):\n"
            "- YOLO detections per tooth\n"
            "- NLP extracted entities\n"
            "- Fusion model scores\n"
            "- Decision rules triggered"
        ),
    )

    # =====================================================
    # PATIENT-SAFE OUTPUT
    # =====================================================

    # (existing field) Keep: explanation shown to patient
    patient_explanation = models.TextField(
        verbose_name=_("Patient Explanation"),
        help_text=_(
            "Safe explanation shown to patient. "
            "Can be brief summary or the main explanation section."
        ),
    )

    # ✅ NEW: Detailed unified report text (full narrative)
    report_text = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Detailed Report Text"),
        help_text=_(
            "Full unified detailed report generated by fusion model. "
            "This is the main narrative report content displayed to patient."
        ),
    )

    recommendations = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Recommendations"),
        help_text=_(
            "General next steps and advice "
            "(non-medical, educational guidance)"
        ),
    )

    # =====================================================
    # REVIEW & LIFECYCLE
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
        help_text=_("Supervisor who reviewed this AI output"),
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

    # =====================================================
    # DJANGO META
    # =====================================================
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
            models.Index(fields=["confidence_level"]),
            models.Index(fields=["severity_level"]),
            models.Index(fields=["urgency_level"]),
        ]

    # =====================================================
    # STRING REPRESENTATION
    # =====================================================
    def __str__(self):
        headline = self.primary_diagnosis or self.diagnosis_label
        return (
            f"AI Diagnosis | "
            f"Patient: {self.patient.email} | "
            f"Case: {self.case_id} | "
            f"Headline: {headline} | "
            f"Date: {self.created_at.date()}"
        )
