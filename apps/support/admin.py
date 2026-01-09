from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from medismile.admin_mixins import BaseOptimizedAdmin

from .models import SupportTicket, SupportTicketResponse


# ============================================================
# Inline Responses (inside Ticket)
# ============================================================

class SupportTicketResponseInline(admin.TabularInline):
    model = SupportTicketResponse
    extra = 0
    can_delete = False
    show_change_link = False

    readonly_fields = (
        "author",
        "message",
        "is_internal",
        "created_at",
    )

    fields = (
        "author",
        "message",
        "is_internal",
        "created_at",
    )


# ============================================================
# Support Ticket Admin
# ============================================================

@admin.register(SupportTicket)
class SupportTicketAdmin(BaseOptimizedAdmin):
    list_display = (
        "subject",
        "created_by",
        "category",
        "priority",
        "status",
        "assigned_to",
        "created_at",
        "resolved_at",
        "closed_at",
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
    date_hierarchy = "created_at"
    list_select_related = ("created_by", "assigned_to")
    autocomplete_fields = ("created_by", "assigned_to")

    readonly_fields = (
        "id",
        "created_by",
        "created_at",
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
                "created_at",
            )
        }),
        (_("Assignment"), {
            "fields": ("assigned_to",)
        }),
        (_("Resolution"), {
            "fields": (
                "resolution",
                "resolved_at",
                "closed_at",
            )
        }),
    )

    inlines = (SupportTicketResponseInline,)


# ============================================================
# Support Ticket Response Admin (standalone)
# ============================================================

@admin.register(SupportTicketResponse)
class SupportTicketResponseAdmin(BaseOptimizedAdmin):
    list_display = (
        "id",
        "ticket",
        "author",
        "is_internal",
        "created_at",
    )

    list_filter = (
        "is_internal",
        "created_at",
    )

    search_fields = (
        "ticket__subject",
        "author__email",
        "message",
    )

    ordering = ("-created_at",)
    list_select_related = ("ticket", "author")
    autocomplete_fields = ("ticket", "author")

    readonly_fields = (
        "id",
        "ticket",
        "author",
        "message",
        "is_internal",
        "created_at",
    )
