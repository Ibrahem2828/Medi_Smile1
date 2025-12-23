from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Backup


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    """
    لوحة إدارة النسخ الاحتياطية
    توفر عرضًا تفصيليًا لحالة كل نسخة احتياطية
    """

    # ============================================================
    # List View
    # ============================================================

    list_display = [
        'id',
        'backup_type',
        'status_colored',
        'total_size_display',
        'storage_type',
        'created_at',
        'completed_at',
    ]

    list_filter = [
        'backup_type',
        'status',
        'storage_type',
        'created_at',
    ]

    search_fields = [
        'id',
        'description',
        'error_message',
        'database_backup_path',
        'files_backup_path',
    ]

    ordering = ['-created_at']
    list_per_page = 25

    # ============================================================
    # Read-only Fields
    # ============================================================

    readonly_fields = [
        'id',
        'created_at',
        'started_at',
        'completed_at',
        'duration',
        'database_backup_path',
        'files_backup_path',
        'database_size',
        'files_size',
        'total_size',
        'error_message',
    ]

    # ============================================================
    # Fieldsets
    # ============================================================

    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'id',
                'backup_type',
                'status',
                'description',
            )
        }),
        (_('Backup Files'), {
            'fields': (
                'database_backup_path',
                'files_backup_path',
                'database_size',
                'files_size',
                'total_size',
            )
        }),
        (_('Storage'), {
            'fields': (
                'storage_type',
                'storage_path',
            )
        }),
        (_('Timestamps'), {
            'fields': (
                'created_at',
                'started_at',
                'completed_at',
                'duration',
            )
        }),
        (_('Errors'), {
            'fields': ('error_message',),
            'classes': ('collapse',),
        }),
    )

    # ============================================================
    # Custom Display Methods
    # ============================================================

    def total_size_display(self, obj):
        """عرض الحجم الإجمالي بشكل مقروء"""
        return self._format_size(obj.total_size)
    total_size_display.short_description = _('Total Size')

    def status_colored(self, obj):
        """عرض حالة النسخة الاحتياطية مع تمييز لوني"""
        color_map = {
            'pending': 'gray',
            'in_progress': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        color = color_map.get(obj.status, 'black')
        return f'<span style="color:{color}; font-weight:bold;">{obj.get_status_display()}</span>'
    status_colored.allow_tags = True
    status_colored.short_description = _('Status')

    # ============================================================
    # Helpers
    # ============================================================

    def _format_size(self, size_bytes):
        """تحويل الحجم من bytes إلى شكل مقروء"""
        if not size_bytes:
            return "0 B"

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"
