# apps/cases/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from medismile.admin_mixins import BaseOptimizedAdmin

from .models import (
    Case,
    CaseHistory,
    CaseAssignmentRequest,
    CaseSession,
)


# ============================================================
# Case Admin
# ============================================================
@admin.register(Case)
class CaseAdmin(BaseOptimizedAdmin):
    list_display = (
        "title",
        "patient",
        "student",
        "supervisor",
        "university",
        "status",
        "priority",
        "is_public",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "is_public",
        "university",
    )

    search_fields = (
        "title",
        "description",
        "patient__email",
        "student__email",
        "supervisor__email",
    )

    ordering = ("-created_at",)

    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (_("Case Information"), {
            "fields": (
                "id",
                "title",
                "description",
                "priority",
                "status",
                "is_public",
            )
        }),
        (_("Assignments"), {
            "fields": (
                "patient",
                "student",
                "supervisor",
                "university",
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
        # Prevent hard delete to preserve medical history
        return False


# ============================================================
# Case History (Read-Only Audit)
# ============================================================
@admin.register(CaseHistory)
class CaseHistoryAdmin(BaseOptimizedAdmin):
    list_display = (
        "case",
        "action",
        "performed_by",
        "created_at",
    )

    list_filter = ("action", "created_at")
    search_fields = ("case__title", "performed_by__email")

    readonly_fields = (
        "id",
        "case",
        "action",
        "description",
        "performed_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================
# Assignment Requests
# ============================================================
@admin.register(CaseAssignmentRequest)
class CaseAssignmentRequestAdmin(BaseOptimizedAdmin):
    list_display = (
        "case",
        "student",
        "status",
        "created_at",
        "updated_at",
    )

    list_filter = ("status", "created_at")
    search_fields = ("case__title", "student__email")

    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": (
                "case",
                "student",
                "message",
                "status",
                "supervisor_response",
            )
        }),
        (_("System"), {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )


# ============================================================
# Case Sessions
# ============================================================
@admin.register(CaseSession)
class CaseSessionAdmin(BaseOptimizedAdmin):
    list_display = (
        "case",
        "student",
        "supervisor",
        "status",
        "created_at",
    )

    list_filter = ("status", "created_at")
    search_fields = (
        "case__title",
        "student__email",
        "supervisor__email",
    )

    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (_("Session"), {
            "fields": (
                "case",
                "student",
                "supervisor",
                "status",
            )
        }),
        (_("Clinical Data"), {
            "fields": (
                "notes",
                "supervisor_feedback",
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
        # Preserve medical/educational records
        return False
