import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User


# ============================================================
# Support Ticket
# ============================================================

class SupportTicket(models.Model):
    """
    Technical support ticket.

    Used strictly for:
    - Technical issues
    - System errors
    - Account problems
    - Feature requests
    NOT for medical or academic decisions.
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

    # --------------------------------------------------------
    # Relations
    # --------------------------------------------------------
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
        limit_choices_to={"role": "tech_support"},
        verbose_name=_("Assigned To (Tech Support)"),
    )

    # --------------------------------------------------------
    # Core Fields
    # --------------------------------------------------------
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.TECHNICAL,
        verbose_name=_("Category"),
    )

    subject = models.CharField(
        max_length=200,
        verbose_name=_("Subject"),
    )

    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Detailed description of the issue."),
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name=_("Priority"),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name=_("Status"),
    )

    resolution = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Resolution"),
        help_text=_("Filled by technical support when resolving the ticket."),
    )

    # --------------------------------------------------------
    # Timestamps
    # --------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Resolved At"))
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Closed At"))

    # --------------------------------------------------------
    # Meta
    # --------------------------------------------------------
    class Meta:
        db_table = "support_tickets"
        verbose_name = _("Support Ticket")
        verbose_name_plural = _("Support Tickets")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["category"]),
            models.Index(fields=["created_at"]),
        ]

    # --------------------------------------------------------
    # Business Rules
    # --------------------------------------------------------
    def clean(self):
        if self.assigned_to and self.assigned_to.role != "tech_support":
            raise ValidationError(_("Ticket can only be assigned to technical support."))

        if self.status == self.Status.RESOLVED and not self.resolution:
            raise ValidationError(_("Resolved tickets must include a resolution."))

        if self.status == self.Status.CLOSED and not self.closed_at:
            raise ValidationError(_("Closed tickets must have a closed_at timestamp."))

    def __str__(self):
        return f"{self.subject} ({self.get_status_display()})"


# ============================================================
# Support Ticket Response
# ============================================================

class SupportTicketResponse(models.Model):
    """
    Response inside a support ticket.

    Acts as a secure, auditable communication channel.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="responses",
        verbose_name=_("Ticket"),
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="support_ticket_responses",
        verbose_name=_("Author"),
    )

    message = models.TextField(
        verbose_name=_("Message"),
    )

    is_internal = models.BooleanField(
        default=False,
        verbose_name=_("Internal Message"),
        help_text=_("Visible only to technical support staff."),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = "support_ticket_responses"
        verbose_name = _("Support Ticket Response")
        verbose_name_plural = _("Support Ticket Responses")
        ordering = ["created_at"]

    def clean(self):
        # Internal messages must be written by tech support
        if self.is_internal and self.author.role != "tech_support":
            raise ValidationError(_("Only technical support can write internal messages."))

    def __str__(self):
        return f"Response by {self.author.email} on ticket {self.ticket.id}"
