from django.contrib import admin
from .models import SupportTicket, SupportTicketResponse


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['subject', 'user', 'category', 'priority', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'category', 'created_at']
    search_fields = ['subject', 'message', 'user__email', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'resolved_at']
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('id', 'user', 'category', 'subject', 'message', 'priority', 'status')
        }),
        ('التعيين', {
            'fields': ('assigned_to',)
        }),
        ('الحل', {
            'fields': ('resolution', 'resolved_at')
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(SupportTicketResponse)
class SupportTicketResponseAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'user', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['message', 'ticket__subject', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']

