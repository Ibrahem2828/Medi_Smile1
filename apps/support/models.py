import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User, Role


class SupportTicket(models.Model):
    """
    Technical support ticket.
    Used strictly for system / technical / account issues.
    """

    class Category(models.TextChoices):
        TECHNICAL = "technical", _("Technical Problem")
        ACCOUNT = "account", _("Account Issue")
        FEATURE = "feature", _("Feature Request")
        BUG = "bug", _("Bug Report")
        OTHER = "other", _("Other")

    class Priority(models.TextChoices):
        URGENT = "urgent", _("Urgent")
        MEDIUM = "medium", _("Medium")
        LOW = "low", _("Low")

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        IN_PROGRESS = "in_progress", _("In Progress")
        RESOLVED = "resolved", _("Resolved")
        CLOSED = "closed", _("Closed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="support_tickets",
        verbose_name=_("Created By"),
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_support_tickets",
        limit_choices_to={"role__name": Role.TECH_SUPPORT},
        verbose_name=_("Assigned Tech Support"),
    )

    # optional context (future analytics)
    related_app = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="accounts / cases / appointments / community",
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.TECHNICAL,
    )

    subject = models.CharField(max_length=200)
    description = models.TextField()

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    resolution = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["assigned_to"]),
        ]

    def clean(self):
        if self.assigned_to and self.assigned_to.role.name != Role.TECH_SUPPORT:
            raise ValidationError(_("Ticket can only be assigned to tech support."))

        if self.status == self.Status.RESOLVED and not self.resolution:
            raise ValidationError(_("Resolved tickets require a resolution."))

    def save(self, *args, **kwargs):
        if self.status == self.Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()

        if self.status == self.Status.CLOSED and not self.closed_at:
            self.closed_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subject} ({self.status})"


class SupportTicketResponse(models.Model):
    """
    Response inside support ticket (auditable communication).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="responses",
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="support_responses",
    )

    message = models.TextField()

    is_internal = models.BooleanField(
        default=False,
        help_text="Visible only to tech support",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def clean(self):
        if self.is_internal and self.author.role.name != Role.TECH_SUPPORT:
            raise ValidationError(_("Only tech support can add internal notes."))
