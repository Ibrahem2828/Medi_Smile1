from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin configuration for Notification model.
    Notifications are treated as audit records and should be mostly read-only.
    """

    list_display = (
        "id",
        "title",
        "notification_type",
        "sender",
        "recipient",
        "status",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "status",
        "is_read",
        "created_at",
    )

    search_fields = (
        "title",
        "message",
        "sender__username",
        "sender__email",
        "recipient__username",
        "recipient__email",
    )

    ordering = ("-created_at",)

    list_select_related = (
        "sender",
        "recipient",
        "appointment",
        "content",
    )

    readonly_fields = (
        "id",
        "sender",
        "recipient",
        "notification_type",
        "appointment",
        "content",
        "proposed_changes",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (_("Core Information"), {
            "fields": (
                "id",
                "notification_type",
                "title",
                "message",
                "status",
                "is_read",
            )
        }),
        (_("Relations"), {
            "fields": (
                "sender",
                "recipient",
                "appointment",
                "content",
            )
        }),
        (_("Advanced / System"), {
            "fields": (
                "proposed_changes",
                "response_message",
                "created_at",
                "updated_at",
            )
        }),
    )

    def has_add_permission(self, request):
        # Notifications should be created by the system only
        return False
