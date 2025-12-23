# apps/support/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import SupportTicket, SupportTicketResponse


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "created_by",
        "category",
        "priority",
        "status",
        "assigned_to",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "category",
        "created_at",
    )

    search_fields = (
        "subject",
        "description",
        "created_by__email",
        "created_by__username",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "id",
        "created_by",
        "created_at",
        "updated_at",
        "resolved_at",
        "closed_at",
    )

    fieldsets = (
        (_("Basic Information"), {
            "fields": (
                "id",
                "created_by",
                "category",
                "subject",
                "description",
                "priority",
                "status",
            )
        }),
        (_("Assignment"), {
            "fields": (
                "assigned_to",
            )
        }),
        (_("Resolution"), {
            "fields": (
                "resolution",
                "resolved_at",
                "closed_at",
            )
        }),
        (_("Timestamps"), {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )
