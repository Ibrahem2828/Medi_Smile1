# apps/reports/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from medismile.admin_mixins import BaseOptimizedAdmin

from .models import Report


@admin.register(Report)
class ReportAdmin(BaseOptimizedAdmin):
    """
    Admin configuration for Reports.

    Reports are legally/academically sensitive:
    - No deletion from admin
    - No manual add from admin (generated via system/services)
    """

    # ============================================================
    # List View
    # ============================================================
    list_display = (
        "id",
        "author",
        "report_type",
        "target_type",
        "status",
        "university",
        "approved_by",
        "approved_at",
        "is_active",
    )

    list_filter = (
        "report_type",
        "status",
        "is_active",
        "university",
        "created_at",
    )

    search_fields = (
        "author__username",
        "author__email",
        "title",
        "description",
    )

    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    list_select_related = (
        "author",
        "university",
        "approved_by",
    )
    autocomplete_fields = ("author", "student", "university", "approved_by")

    # ============================================================
    # Readonly & Protection
    # ============================================================
    readonly_fields = (
        "id",
        "generated_at",
        "created_at",
        "updated_at",
    )

    actions = None  # prevent bulk delete etc.

    # ============================================================
    # Detail View Layout
    # ============================================================
    fieldsets = (
        (
            _("Core Information"),
            {
                "fields": (
                    "id",
                    "author",
                    "author_role",
                    "student",
                    "university",
                    "report_type",
                    "target_type",
                    "target_id",
                    "status",
                    "title",
                    "description",
                )
            },
        ),
        (
            _("Report File"),
            {
                "fields": ("file_url",),
                "description": _("Link or path to the generated report file."),
            },
        ),
        (
            _("Snapshot"),
            {
                "fields": ("snapshot_data",),
                "description": _("Frozen snapshot used for analytics/statistical reports."),
            },
        ),
        (
            _("Review"),
            {
                "fields": (
                    "review_notes",
                    "approved_by",
                    "approved_at",
                    "submitted_at",
                    "rejected_at",
                    "locked_at",
                )
            },
        ),
        (
            _("System Status"),
            {
                "fields": (
                    "is_active",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    # ============================================================
    # Permissions Control
    # ============================================================
    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    # ============================================================
    # Query Optimization
    # ============================================================
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("student", "university", "generated_by")
