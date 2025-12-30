# apps/ai/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import AIDiagnosis


@admin.register(AIDiagnosis)
class AIDiagnosisAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "patient",
        "case",
        "primary_diagnosis",
        "diagnosis_label",
        "confidence_level",
        "severity_level",
        "urgency_level",
        "status",
        "reviewed_at",
    )
    list_filter = ("status", "confidence_level", "severity_level", "urgency_level", "created_at")
    search_fields = ("patient__email", "patient__username", "primary_diagnosis", "diagnosis_label", "raw_symptoms")
    readonly_fields = [f.name for f in AIDiagnosis._meta.fields]
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 30
    list_select_related = ("patient", "case", "requested_by", "reviewed_by")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
