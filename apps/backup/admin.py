from django.contrib import admin
from .models import Backup


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    """إدارة النسخ الاحتياطية في لوحة الإدارة"""
    
    list_display = [
        'id',
        'backup_type',
        'status',
        'total_size_display',
        'created_at',
        'completed_at',
        'storage_type'
    ]
    
    list_filter = [
        'backup_type',
        'status',
        'storage_type',
        'created_at'
    ]
    
    search_fields = [
        'id',
        'description',
        'error_message'
    ]
    
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
        'error_message'
    ]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('id', 'backup_type', 'status', 'description')
        }),
        ('الملفات', {
            'fields': (
                'database_backup_path',
                'files_backup_path',
                'database_size',
                'files_size',
                'total_size'
            )
        }),
        ('التخزين', {
            'fields': ('storage_type', 'storage_path')
        }),
        ('الطوابع الزمنية', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration')
        }),
        ('الأخطاء', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def total_size_display(self, obj):
        """عرض الحجم الإجمالي"""
        return self._format_size(obj.total_size)
    total_size_display.short_description = 'الحجم الإجمالي'
    
    def _format_size(self, size_bytes):
        """تحويل الحجم من bytes إلى شكل مقروء"""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"














