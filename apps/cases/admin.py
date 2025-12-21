from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Case,
    CaseHistory,
    CaseAssignmentRequest,
)


# ============================================================
# Inline Admins
# ============================================================

class CaseHistoryInline(admin.TabularInline):
    """
    Read-only inline for case history (audit trail).
    """
    model = CaseHistory
    extra = 0
    can_delete = False
    readonly_fields = (
        "action",
        "description",
        "performed_by",
        "created_at",
    )

    def has_add_permission(self, request, obj=None):
        return False


class CaseAssignmentRequestInline(admin.TabularInline):
    """
    Inline view for student assignment requests.
    """
    model = CaseAssignmentRequest
    extra = 0
    readonly_fields = (
        "student",
        "message",
        "status",
        "supervisor_response",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request, obj=None):
        return False


# ============================================================
# Case Admin
# ============================================================

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    """
    Admin interface for medical cases.
    """

    list_display = (
        "id",
        "title",
        "patient",
        "student",
        "supervisor",
        "status",
        "priority",
        "is_public",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "is_public",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "patient__email",
        "student__email",
        "supervisor__email",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

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
        (_("Relations"), {
            "fields": (
                "patient",
                "student",
                "supervisor",
            )
        }),
        (_("Timestamps"), {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    inlines = [
        CaseAssignmentRequestInline,
        CaseHistoryInline,
    ]

    # --------------------------------------------------------
    # Permissions & Safety
    # --------------------------------------------------------

    def has_delete_permission(self, request, obj=None):
        """
        Prevent deleting closed cases.
        """
        if obj and obj.status == Case.Status.CLOSED:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        """
        Make closed cases fully read-only.
        """
        if obj and obj.status == Case.Status.CLOSED:
            return [field.name for field in obj._meta.fields]
        return self.readonly_fields


# ============================================================
# Case History Admin
# ============================================================

@admin.register(CaseHistory)
class CaseHistoryAdmin(admin.ModelAdmin):
    """
    Admin view for case audit logs.
    """

    list_display = (
        "id",
        "case",
        "action",
        "performed_by",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "case__title",
        "performed_by__email",
    )

    readonly_fields = (
        "id",
        "case",
        "action",
        "description",
        "performed_by",
        "created_at",
    )

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================
# Case Assignment Request Admin
# ============================================================

@admin.register(CaseAssignmentRequest)
class CaseAssignmentRequestAdmin(admin.ModelAdmin):
    """
    Admin view for case assignment requests.
    """

    list_display = (
        "id",
        "case",
        "student",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "case__title",
        "student__email",
    )

    readonly_fields = (
        "id",
        "case",
        "student",
        "message",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (_("Assignment Request"), {
            "fields": (
                "case",
                "student",
                "message",
                "status",
            )
        }),
        (_("Supervisor Response"), {
            "fields": (
                "supervisor_response",
            )
        }),
        (_("Timestamps"), {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    def has_add_permission(self, request):
        return False
