# apps/audit/models.py

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import User
from apps.universities.models import University


class AuditAction(models.TextChoices):
    LOGIN = "login", _("Login")
    LOGOUT = "logout", _("Logout")

    CREATE = "create", _("Create")
    UPDATE = "update", _("Update")
    DELETE = "delete", _("Delete")

    VIEW = "view", _("View")
    DOWNLOAD = "download", _("Download")
    UPLOAD = "upload", _("Upload")

    ASSIGN = "assign", _("Assign")
    UNASSIGN = "unassign", _("Unassign")

    APPROVE = "approve", _("Approve")
    REJECT = "reject", _("Reject")

    CONFIRM = "confirm", _("Confirm")
    CANCEL = "cancel", _("Cancel")
    COMPLETE = "complete", _("Complete")

    SUBMIT = "submit", _("Submit")
    FINALIZE = "finalize", _("Finalize")

    OTHER = "other", _("Other")


class AuditLog(models.Model):
    """
    Immutable audit log entry.
    Used for tracking all critical actions across the system.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # =====================================================
    # Actor
    # =====================================================
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("User"),
        help_text=_("User who performed the action"),
    )

    university = models.ForeignKey(
        University,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("University"),
        help_text=_("University scope of the action"),
    )

    # =====================================================
    # Action
    # =====================================================
    action = models.CharField(
        max_length=30,
        choices=AuditAction.choices,
        verbose_name=_("Action"),
    )

    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Human-readable description of the action"),
    )

    # =====================================================
    # Target Object (Generic)
    # =====================================================
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Target Content Type"),
    )

    object_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("Target Object ID"),
    )

    content_object = GenericForeignKey("content_type", "object_id")

    # =====================================================
    # Context / Metadata
    # =====================================================
    metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Metadata"),
        help_text=_("Additional contextual data for auditing"),
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name=_("IP Address"),
    )

    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("User Agent"),
    )

    # =====================================================
    # Timestamp
    # =====================================================
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    # =====================================================
    # Meta
    # =====================================================
    class Meta:
        db_table = "audit_logs"
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "action"]),
            models.Index(fields=["university"]),
            models.Index(fields=["created_at"]),
        ]

    # =====================================================
    # Protection (Immutable)
    # =====================================================
    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Audit logs are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Audit logs cannot be deleted.")

    def __str__(self):
        user_display = self.user.email if self.user else _("Anonymous")
        return f"{user_display} | {self.action} | {self.created_at}"
