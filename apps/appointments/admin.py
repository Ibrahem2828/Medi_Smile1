# apps/appointments/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """
    Appointment Admin Configuration.

    - Readable overview for admins and IT support
    - No hard delete (medical integrity)
    """

    list_display = (
        "appointment_date",
        "case",
        "patient",
        "student",
        "supervisor",
        "status",
        "is_follow_up",
        "is_archived",
        "created_at",
    )

    list_filter = (
        "status",
        "is_follow_up",
        "is_archived",
        "appointment_date",
    )

    search_fields = (
        "patient__email",
        "student__email",
        "supervisor__email",
        "case__title",
    )

    ordering = ("-appointment_date",)

    readonly_fields = (
        "id",
        "case",
        "patient",
        "student",
        "supervisor",
        "created_by",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (_("Appointment Details"), {
            "fields": (
                "appointment_date",
                "status",
                "is_follow_up",
                "notes",
                "is_archived",
            )
        }),
        (_("Relations"), {
            "fields": (
                "case",
                "patient",
                "student",
                "supervisor",
                "created_by",
            )
        }),
        (_("System"), {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    def has_delete_permission(self, request, obj=None):
        """
        Prevent hard deletion to preserve medical & academic records.
        """
        return False

    def has_add_permission(self, request):
        """
        Creation is handled via API (students/supervisors).
        """
        return False
