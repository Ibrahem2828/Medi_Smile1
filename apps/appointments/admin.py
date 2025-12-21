# apps/appointments/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Appointment model.
    Intended for:
    - University Admin (read / limited edit)
    - IT Support (audit & debugging)
    """

    # ---------------------------------------------------------
    # Display
    # ---------------------------------------------------------
    list_display = (
        "id",
        "appointment_date",
        "status",
        "patient_email",
        "student_email",
        "supervisor_email",
        "case_id",
        "is_archived",
        "created_at",
    )

    list_filter = (
        "status",
        "is_archived",
        "appointment_date",
        "created_at",
    )

    search_fields = (
        "patient__email",
        "student__email",
        "supervisor__email",
        "case__id",
    )

    ordering = ("-appointment_date",)

    date_hierarchy = "appointment_date"

    # ---------------------------------------------------------
    # Read-only & Safety
    # ---------------------------------------------------------
    readonly_fields = (
        "id",
        "patient",
        "student",
        "supervisor",
        "case",
        "created_by",
        "created_at",
        "updated_at",
    )

    # Prevent accidental deletes (medical record)
    def has_delete_permission(self, request, obj=None):
        return False

    # ---------------------------------------------------------
    # Fieldsets
    # ---------------------------------------------------------
    fieldsets = (
        (
            _("Core Information"),
            {
                "fields": (
                    "id",
                    "case",
                    "patient",
                    "student",
                    "supervisor",
                )
            },
        ),
        (
            _("Appointment Details"),
            {
                "fields": (
                    "appointment_date",
                    "status",
                    "is_archived",
                    "notes",
                )
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    # ---------------------------------------------------------
    # Custom display helpers
    # ---------------------------------------------------------
    @admin.display(description=_("Patient"))
    def patient_email(self, obj):
        return obj.patient.email if obj.patient else "-"

    @admin.display(description=_("Student"))
    def student_email(self, obj):
        return obj.student.email if obj.student else "-"

    @admin.display(description=_("Supervisor"))
    def supervisor_email(self, obj):
        return obj.supervisor.email if obj.supervisor else "-"

    @admin.display(description=_("Case ID"))
    def case_id(self, obj):
        return obj.case.id if obj.case else "-"
