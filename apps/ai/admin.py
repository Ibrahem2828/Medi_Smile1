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
        "diagnosis_label",
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
        "diagnosis_label",
        "raw_symptoms",
        "normalized_symptoms",
    )

    readonly_fields = (
        "id",
        "case",
        "patient",
        "requested_by",
        "raw_symptoms",
        "normalized_symptoms",
        "diagnosis_label",
        "confidence_level",
        "severity_level",
        "urgency_level",
        "patient_explanation",
        "recommendations",
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
        (_("AI Output (Technical)"), {
            "fields": (
                "diagnosis_label",
                "confidence_level",
                "severity_level",
                "urgency_level",
                "ai_metadata",
            )
        }),
        (_("Patient Explanation"), {
            "fields": (
                "patient_explanation",
                "recommendations",
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
        # AI diagnoses are created programmatically only
        return False

    def has_delete_permission(self, request, obj=None):
        # Preserve medical audit trail
        return False
