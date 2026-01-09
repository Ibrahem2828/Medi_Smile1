# apps/audit/admin.py
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from medismile.admin_mixins import BaseOptimizedAdmin

from .models import AuditLog


@admin.register(ContentType)
class ContentTypeAdmin(BaseOptimizedAdmin):
    search_fields = ("app_label", "model")
    list_display = ("app_label", "model")
    ordering = ("app_label", "model")


@admin.register(AuditLog)
class AuditLogAdmin(BaseOptimizedAdmin):
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
    autocomplete_fields = ("user", "university", "content_type")
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
