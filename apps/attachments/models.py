# apps/attachments/models.py
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role
from apps.cases.models import Case
from apps.appointments.models import Appointment


class Attachment(models.Model):
    """
    Medical / educational attachment.

    Attached to a specific Appointment within a Case.
    Used for:
    - Before / After images
    - Clinical reports
    - Supporting documents
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
        OTHER = "other", _("Other")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --------------------------------------------------
    # Relations
    # --------------------------------------------------
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("Case"),
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("Appointment"),
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="uploaded_attachments",
        limit_choices_to={"role__name": Role.STUDENT},
        verbose_name=_("Uploaded By (Student)"),
    )

    # --------------------------------------------------
    # File data
    # --------------------------------------------------
    file = models.FileField(upload_to="attachments/")
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100)

    file_category = models.CharField(
        max_length=20,
        choices=FileCategory.choices,
    )

    attachment_type = models.CharField(
        max_length=30,
        choices=AttachmentType.choices,
    )

    is_visible_to_patient = models.BooleanField(
        default=True,
        verbose_name=_("Visible to patient"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["case"]),
            models.Index(fields=["appointment"]),
            models.Index(fields=["attachment_type"]),
        ]

    # --------------------------------------------------
    # Business rules
    # --------------------------------------------------
    def clean(self):
        if self.uploaded_by.role.name != Role.STUDENT:
            raise ValidationError(_("Only students can upload attachments."))

        if self.appointment.case_id != self.case_id:
            raise ValidationError(_("Appointment does not belong to this case."))

        if self.attachment_type == self.AttachmentType.AFTER_IMAGE:
            exists = Attachment.objects.filter(
                appointment=self.appointment,
                attachment_type=self.AttachmentType.BEFORE_IMAGE,
            ).exists()
            if not exists:
                raise ValidationError(_("Before image must exist first."))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.original_filename
