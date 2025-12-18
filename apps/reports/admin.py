from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'report_type', 'university', 'generated_at', 'generated_by', 'is_active')
    list_filter = ('report_type', 'is_active', 'generated_at', 'university')
    search_fields = ('student__username', 'student__email', 'title', 'description')
    readonly_fields = ('id', 'generated_at', 'created_at', 'updated_at')
    date_hierarchy = 'generated_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'student', 'university', 'report_type', 'title', 'description')
        }),
        ('File Information', {
            'fields': ('file_url',)
        }),
        ('Metadata', {
            'fields': ('generated_by', 'generated_at', 'is_active', 'created_at', 'updated_at')
        }),
    )




















