# apps/reports/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
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
        "student",
        "report_type",
        "university",
        "generated_by",
        "generated_at",
        "is_active",
    )

    list_filter = (
        "report_type",
        "is_active",
        "university",
        "generated_at",
    )

    search_fields = (
        "student__username",
        "student__email",
        "student__first_name",
        "student__last_name",
        "title",
        "description",
    )

    ordering = ("-generated_at",)
    date_hierarchy = "generated_at"

    list_select_related = (
        "student",
        "university",
        "generated_by",
    )

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
                    "student",
                    "university",
                    "report_type",
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
            _("Generation Metadata"),
            {
                "fields": (
                    "generated_by",
                    "generated_at",
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
