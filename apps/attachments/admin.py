# apps/attachments/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Attachment model.

    Purpose:
    - Technical auditing
    - File inspection
    - Debugging & support
    NOT for medical or academic decision making.
    """

    # --------------------------------------------------
    # List view
    # --------------------------------------------------
    list_display = (
        "original_filename",
        "attachment_type",
        "file_category",
        "file_size",
        "uploaded_by",
        "is_visible_to_patient",
        "created_at",
    )

    list_filter = (
        "attachment_type",
        "file_category",
        "is_visible_to_patient",
        "created_at",
    )

    search_fields = (
        "original_filename",
        "uploaded_by__email",
        "uploaded_by__username",
        "mime_type",
    )

    ordering = ("-created_at",)

    # --------------------------------------------------
    # Read-only enforcement
    # --------------------------------------------------
    readonly_fields = (
        "id",
        "file",
        "original_filename",
        "attachment_type",
        "file_category",
        "file_size",
        "mime_type",
        "case",
        "session",
        "uploaded_by",
        "is_visible_to_patient",
        "created_at",
    )

    # --------------------------------------------------
    # Field layout
    # --------------------------------------------------
    fieldsets = (
        (_("File Information"), {
            "fields": (
                "file",
                "original_filename",
                "attachment_type",
                "file_category",
                "file_size",
                "mime_type",
            )
        }),
        (_("Medical Relations"), {
            "fields": (
                "case",
                "session",
            )
        }),
        (_("Ownership & Visibility"), {
            "fields": (
                "uploaded_by",
                "is_visible_to_patient",
            )
        }),
        (_("System"), {
            "fields": (
                "id",
                "created_at",
            )
        }),
    )

    # --------------------------------------------------
    # Permissions
    # --------------------------------------------------
    def has_add_permission(self, request):
        """Prevent manual upload from admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent editing attachment metadata."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow delete ONLY for superusers."""
        return request.user.is_superuser
