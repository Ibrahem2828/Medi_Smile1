# apps/ai/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import AIDiagnosis


@admin.register(AIDiagnosis)
class AIDiagnosisAdmin(admin.ModelAdmin):
    """
    Admin configuration for AI Diagnoses.
    AI results are read-only and auditable.
    """

    list_display = (
        "created_at",
        "patient",
        "case",
        "primary_diagnosis",
        "confidence_level",
        "severity_level",
        "urgency_level",
        "status",
    )

    list_filter = (
        "status",
        "confidence_level",
        "severity_level",
        "urgency_level",
        "created_at",
    )

    search_fields = (
        "patient__email",
        "primary_diagnosis",
        "diagnosis_label",
        "raw_symptoms",
    )

    readonly_fields = (
        "id",
        "case",
        "patient",
        "requested_by",
        "raw_symptoms",
        "normalized_symptoms",
        "diagnosis_label",
        "primary_diagnosis",
        "detected_findings",
        "patient_explanation",
        "report_text",
        "recommendations",
        "confidence_level",
        "severity_level",
        "urgency_level",
        "ai_metadata",
        "status",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )

    fieldsets = (
        (_("Context"), {
            "fields": (
                "case",
                "patient",
                "requested_by",
            )
        }),
        (_("Input"), {
            "fields": (
                "raw_symptoms",
                "normalized_symptoms",
            )
        }),
        (_("Diagnosis Summary"), {
            "fields": (
                "primary_diagnosis",
                "confidence_level",
                "severity_level",
                "urgency_level",
            )
        }),
        (_("Detected Findings"), {
            "fields": (
                "detected_findings",
            )
        }),
        (_("Patient Report"), {
            "fields": (
                "patient_explanation",
                "report_text",
                "recommendations",
            )
        }),
        (_("Technical Metadata"), {
            "fields": (
                "diagnosis_label",
                "ai_metadata",
            )
        }),
        (_("Lifecycle"), {
            "fields": (
                "status",
                "reviewed_by",
                "reviewed_at",
                "created_at",
            )
        }),
    )

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False  # Created programmatically only

    def has_delete_permission(self, request, obj=None):
        return False  # Preserve audit trail
