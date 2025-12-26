# apps/notifications/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "notification_type",
        "recipient",
        "sender",
        "priority",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "priority",
        "is_read",
        "created_at",
    )

    search_fields = (
        "title",
        "message",
        "recipient__username",
        "sender__username",
    )

    readonly_fields = (
        "id",
        "sender",
        "recipient",
        "notification_type",
        "title",
        "message",
        "appointment",
        "target_content_type",
        "target_object_id",
        "created_at",
    )

    fieldsets = (
        (
            _("Core Information"),
            {
                "fields": (
                    "id",
                    "notification_type",
                    "priority",
                    "is_read",
                )
            },
        ),
        (
            _("Actors"),
            {
                "fields": (
                    "sender",
                    "recipient",
                )
            },
        ),
        (
            _("Content"),
            {
                "fields": (
                    "title",
                    "message",
                    "appointment",
                    "target_content_type",
                    "target_object_id",
                )
            },
        ),
        (
            _("Metadata"),
            {
                "fields": (
                    "created_at",
                )
            },
        ),
    )

    ordering = ("-created_at",)
