# apps/community/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Content


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "status",
        "author",
        "university",
        "is_public",
        "is_featured",
        "created_at",
    )

    list_filter = ("status", "is_public", "is_featured", "university", "created_at")
    search_fields = ("title", "description", "author__username", "author__email")
    ordering = ("-created_at",)

    readonly_fields = ("id", "created_at", "updated_at", "approved_at")
    list_select_related = ("author", "university", "approved_by")

    fieldsets = (
        (_("Content"), {"fields": ("id", "title", "description", "content_type", "category", "tags")}),
        (_("Media"), {"fields": ("file", "url")}),
        (_("Ownership"), {"fields": ("author", "university")}),
        (_("Moderation"), {"fields": ("status", "approved_by", "approved_at", "rejection_reason")}),
        (_("Visibility"), {"fields": ("is_public", "is_featured", "view_count")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )

    def has_delete_permission(self, request, obj=None):
        # protect academic content history
        return False
