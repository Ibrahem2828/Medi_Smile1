# apps/attachments/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """
    Attachment Admin Configuration.

    - Read-only medical & academic attachments
    - No hard delete to preserve integrity
    """

    list_display = (
        "original_filename",
        "attachment_type",
        "file_category",
        "case",
        "appointment",
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
        "case__title",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "id",
        "case",
        "appointment",
        "uploaded_by",
        "original_filename",
        "file_size",
        "mime_type",
        "file",
        "created_at",
    )

    fieldsets = (
        (_("Attachment Info"), {
            "fields": (
                "attachment_type",
                "file_category",
                "is_visible_to_patient",
            )
        }),
        (_("Relations"), {
            "fields": (
                "case",
                "appointment",
                "uploaded_by",
            )
        }),
        (_("File Data"), {
            "fields": (
                "file",
                "original_filename",
                "file_size",
                "mime_type",
            )
        }),
        (_("System"), {
            "fields": (
                "created_at",
            )
        }),
    )

    def has_add_permission(self, request):
        """
        Uploads are handled via API (students only).
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Prevent hard delete of medical attachments.
        """
        return False
