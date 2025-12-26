# apps/audit/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "university",
        "action",
        "content_type",
        "object_id",
    )

    list_filter = ("action", "university", "created_at")
    search_fields = ("user__email", "user__username", "description", "metadata", "ip_address")
    readonly_fields = (
        "id",
        "user",
        "university",
        "action",
        "description",
        "content_type",
        "object_id",
        "metadata",
        "ip_address",
        "user_agent",
        "created_at",
    )

    fieldsets = (
        (_("Actor Information"), {"fields": ("user", "university")}),
        (_("Action Information"), {"fields": ("action", "description")}),
        (_("Target Object"), {"fields": ("content_type", "object_id")}),
        (_("Request Metadata"), {"fields": ("ip_address", "user_agent", "metadata")}),
        (_("Timestamp"), {"fields": ("created_at",)}),
    )

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
