# apps/ai/models.py
import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DiagnosisStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    COMPLETED = "completed", _("Completed")
    PARTIAL = "partial", _("Partial Evidence")
    INSUFFICIENT_EVIDENCE = "insufficient_evidence", _("Insufficient Evidence")
    FAILED = "failed", _("Failed")
    REVIEWED = "reviewed", _("Reviewed by Supervisor")


class ConfidenceLevel(models.TextChoices):
    UNKNOWN = "unknown", _("Unknown")
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")


class SeverityLevel(models.TextChoices):
    UNKNOWN = "unknown", _("Unknown")
    LOW = "low", _("Low")
    MODERATE = "moderate", _("Moderate")
    HIGH = "high", _("High")


class UrgencyLevel(models.TextChoices):
    UNKNOWN = "unknown", _("Unknown")
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
        max_length=30,
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


def _ai_image_upload_path(instance, filename: str) -> str:
    # Never trust the client filename: store under a random name with the
    # extension derived from the *decoded* image format.
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(instance.content_type, "bin")
    return f"ai_uploads/{instance.patient_id}/{uuid.uuid4().hex}.{ext}"


class AIImageUpload(models.Model):
    """
    A dental photo uploaded by a patient for AI analysis.

    Uploaded once via ``POST /api/ai/images/`` and then referenced by id from
    ``POST /api/ai/diagnose/`` (``image_ids``). The vision engine receives the
    stored bytes directly, so the backend never fetches arbitrary URLs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_image_uploads",
        verbose_name=_("Patient"),
    )
    diagnosis = models.ForeignKey(
        AIDiagnosis,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="images",
        verbose_name=_("Diagnosis"),
    )

    image = models.FileField(upload_to=_ai_image_upload_path, verbose_name=_("Image"))
    content_type = models.CharField(max_length=32, verbose_name=_("Content Type"))
    size_bytes = models.PositiveIntegerField(verbose_name=_("Size (bytes)"))
    width = models.PositiveIntegerField(verbose_name=_("Width"))
    height = models.PositiveIntegerField(verbose_name=_("Height"))
    sha256 = models.CharField(max_length=64, verbose_name=_("SHA-256"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        db_table = "ai_image_uploads"
        verbose_name = _("AI Image Upload")
        verbose_name_plural = _("AI Image Uploads")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"AIImageUpload {self.id} | patient={self.patient_id}"
