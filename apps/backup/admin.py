from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from medismile.admin_mixins import BaseOptimizedAdmin

from .models import Backup


@admin.register(Backup)
class BackupAdmin(BaseOptimizedAdmin):
    """
    Admin configuration for backup jobs.
    """

    # ============================================================
    # List View
    # ============================================================

    list_display = [
        "id",
        "backup_type",
        "status_colored",
        "total_size_display",
        "storage_type",
        "created_at",
        "completed_at",
    ]

    list_filter = [
        "backup_type",
        "status",
        "storage_type",
        "created_at",
    ]

    search_fields = [
        "id",
        "description",
        "error_message",
        "database_backup_path",
        "files_backup_path",
    ]

    ordering = ["-created_at"]
    list_per_page = 25

    # ============================================================
    # Read-only Fields
    # ============================================================

    readonly_fields = [
        "id",
        "created_at",
        "started_at",
        "completed_at",
        "duration",
        "database_backup_path",
        "files_backup_path",
        "database_size",
        "files_size",
        "total_size",
        "error_message",
    ]

    # ============================================================
    # Fieldsets
    # ============================================================

    fieldsets = (
        (_("Basic Information"), {
            "fields": (
                "id",
                "backup_type",
                "status",
                "description",
            )
        }),
        (_("Backup Files"), {
            "fields": (
                "database_backup_path",
                "files_backup_path",
                "database_size",
                "files_size",
                "total_size",
            )
        }),
        (_("Storage"), {
            "fields": (
                "storage_type",
                "storage_path",
            )
        }),
        (_("Timestamps"), {
            "fields": (
                "created_at",
                "started_at",
                "completed_at",
                "duration",
            )
        }),
        (_("Errors"), {
            "fields": ("error_message",),
            "classes": ("collapse",),
        }),
    )

    # ============================================================
    # Custom Display Methods
    # ============================================================

    @admin.display(description=_("Total Size"))
    def total_size_display(self, obj):
        return self._format_size(obj.total_size)

    @admin.display(description=_("Status"))
    def status_colored(self, obj):
        color_map = {
            "pending": "#64748b",
            "in_progress": "#0ea5a4",
            "completed": "#16a34a",
            "failed": "#dc2626",
        }
        color = color_map.get(obj.status, "#0f172a")
        return format_html(
            '<span style="color:{}; font-weight:700;">{}</span>',
            color,
            obj.get_status_display(),
        )

    # ============================================================
    # Helpers
    # ============================================================

    def _format_size(self, size_bytes):
        if not size_bytes:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"
