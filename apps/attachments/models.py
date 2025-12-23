# apps/attachments/models.py

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.cases.models import CaseSession


# ============================================================
# Attachment (Medical / Educational Evidence)
# ============================================================

class Attachment(models.Model):
    """
    Medical attachment linked to a treatment session.

    Examples:
    - Before image
    - After image
    - Clinical report
    - Supporting document

    Attachments are immutable once the session is approved.
    """

    class AttachmentType(models.TextChoices):
        BEFORE_IMAGE = "before_image", _("Before Treatment Image")
        AFTER_IMAGE = "after_image", _("After Treatment Image")
        REPORT = "report", _("Clinical Report")
        OTHER = "other", _("Other")

    class FileCategory(models.TextChoices):
        IMAGE = "image", _("Image")
        DOCUMENT = "document", _("Document")
        VIDEO = "video", _("Video")
        AUDIO = "audio", _("Audio")
        OTHER = "other", _("Other")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --------------------------------------------------------
    # File data
    # --------------------------------------------------------
    file = models.FileField(
        upload_to="attachments/",
        verbose_name=_("File"),
    )

    original_filename = models.CharField(
        max_length=255,
        verbose_name=_("Original Filename"),
    )

    file_category = models.CharField(
        max_length=20,
        choices=FileCategory.choices,
        verbose_name=_("File Category"),
    )

    attachment_type = models.CharField(
        max_length=30,
        choices=AttachmentType.choices,
        verbose_name=_("Attachment Type"),
        help_text=_("Medical context of this attachment."),
    )

    file_size = models.PositiveIntegerField(
        verbose_name=_("File Size (bytes)"),
    )

    mime_type = models.CharField(
        max_length=100,
        verbose_name=_("MIME Type"),
    )

    # --------------------------------------------------------
    # Medical relations
    # --------------------------------------------------------
    session = models.ForeignKey(
        CaseSession,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("Treatment Session"),
    )

    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("Case"),
        editable=False,
    )

    # --------------------------------------------------------
    # Ownership & visibility
    # --------------------------------------------------------
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="attachments",
        limit_choices_to={"role": "student"},
        verbose_name=_("Uploaded By (Student)"),
    )

    is_visible_to_patient = models.BooleanField(
        default=True,
        verbose_name=_("Visible to Patient"),
        help_text=_("If true, patient can view this attachment."),
    )

    # --------------------------------------------------------
    # Audit & timestamps
    # --------------------------------------------------------
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    class Meta:
        db_table = "attachments"
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["case"]),
            models.Index(fields=["session"]),
            models.Index(fields=["attachment_type"]),
        ]

    # --------------------------------------------------------
    # Validation & Business Rules
    # --------------------------------------------------------
    def clean(self):
        """
        Enforce medical and legal rules.
        """

        # Ensure session-case consistency
        if self.session and self.case and self.session.case_id != self.case_id:
            raise ValidationError(_("Session does not belong to the specified case."))

        # Only students can upload
        if self.uploaded_by.role != "student":
            raise ValidationError(_("Only students can upload attachments."))

        # Prevent modification after session approval
        if self.pk:
            previous = Attachment.objects.filter(pk=self.pk).first()
            if previous and self.session.status == CaseSession.Status.APPROVED:
                raise ValidationError(_("Attachments cannot be modified after session approval."))

    def save(self, *args, **kwargs):
        # Auto-fill case from session
        if self.session and not self.case_id:
            self.case = self.session.case

        self.full_clean()
        super().save(*args, **kwargs)

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------
    def __str__(self):
        return f"{self.original_filename} ({self.get_attachment_type_display()})"

    @property
    def is_before_image(self) -> bool:
        return self.attachment_type == self.AttachmentType.BEFORE_IMAGE

    @property
    def is_after_image(self) -> bool:
        return self.attachment_type == self.AttachmentType.AFTER_IMAGE

    @property
    def is_image(self) -> bool:
        return self.file_category == self.FileCategory.IMAGE
