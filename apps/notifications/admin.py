from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'sender', 'recipient', 'notification_type', 'status', 'is_read', 'created_at']
    list_filter = ['notification_type', 'status', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'sender__username', 'recipient__username']
    readonly_fields = ['id', 'created_at', 'updated_at']























