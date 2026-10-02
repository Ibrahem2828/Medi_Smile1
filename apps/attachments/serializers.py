# apps/attachments/serializers.py
import logging
import os

from PIL import Image, UnidentifiedImageError
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse

from medismile.utils.auth import resolve_request_user

from apps.accounts.models import User, Role
from apps.appointments.models import Appointment
from .models import Attachment
from .storage_backends import get_storage_backend, generate_attachment_path

logger = logging.getLogger(__name__)


class AttachmentUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role")
        read_only_fields = fields


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = AttachmentUserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = (
            "id",
            "attachment_type",
            "file_category",
            "file_url",
            "original_filename",
            "file_size",
            "mime_type",
            "is_visible_to_patient",
            "uploaded_by",
            "created_at",
        )

    def get_file_url(self, obj):
        # Medical attachments are downloaded through an authenticated endpoint,
        # never through a storage URL or a public /media/ mount.
        request = self.context.get("request")
        path = reverse("attachment-file", kwargs={"pk": obj.pk})
        return request.build_absolute_uri(path) if request else path


class AttachmentCreateSerializer(serializers.Serializer):
    appointment_id = serializers.UUIDField()
    file = serializers.FileField()
    attachment_type = serializers.ChoiceField(
        choices=Attachment.AttachmentType.choices
    )

    _IMAGE_MIME_BY_FORMAT = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
    }

    def validate_file(self, value):
        if value.size > settings.ATTACHMENT_MAX_BYTES:
            raise serializers.ValidationError(
                _("File is larger than the configured upload limit.")
            )

        # Browser-provided content_type is not evidence.  Read the magic bytes
        # and verify images with Pillow before accepting them.
        try:
            value.seek(0)
            image = Image.open(value)
            image.verify()
            mime_type = self._IMAGE_MIME_BY_FORMAT.get(image.format or "")
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
            value.seek(0)
            header = value.read(8)
            mime_type = "application/pdf" if header.startswith(b"%PDF-") else None
        finally:
            value.seek(0)

        if not mime_type:
            raise serializers.ValidationError(
                _("Only verified JPEG, PNG, WebP, or PDF files are allowed.")
            )
        # DRF calls this method before validate(); attach data via the upload
        # object is unsafe, so stash it in serializer state for create().
        self._verified_mime_type = mime_type
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError(_("Request context missing."))
        user = resolve_request_user(request)

        if not user or not getattr(getattr(user, "role", None), "name", None):
            raise serializers.ValidationError(_("User role is missing; contact admin."))

        if user.role.name != Role.STUDENT:
            raise serializers.ValidationError(_("Only students can upload attachments."))

        try:
            appointment = Appointment.objects.select_related(
                "case", "student"
            ).get(id=attrs["appointment_id"])
        except Appointment.DoesNotExist:
            raise serializers.ValidationError(_("Appointment not found."))

        if appointment.student_id != user.id:
            raise serializers.ValidationError(_("You are not assigned to this appointment."))

        attrs["appointment"] = appointment
        attrs["case"] = appointment.case
        attrs["uploaded_by"] = user
        return attrs

    def create(self, validated_data):
        file = validated_data["file"]
        storage = get_storage_backend()

        try:
            path = generate_attachment_path(original_filename=file.name)
            storage.save(path, file)
        except Exception as exc:
            logger.exception("Attachment storage save failed", exc_info=exc)
            raise serializers.ValidationError({"file": _("Failed to save file. Please try again later.")})

        try:
            return Attachment.objects.create(
                appointment=validated_data["appointment"],
                case=validated_data["case"],
                uploaded_by=validated_data["uploaded_by"],
                file=path,
                original_filename=os.path.basename(file.name)[:255],
                file_size=file.size,
                mime_type=getattr(self, "_verified_mime_type", None),
                attachment_type=validated_data["attachment_type"],
                file_category=(
                    Attachment.FileCategory.IMAGE
                    if getattr(self, "_verified_mime_type", "").startswith("image/")
                    else Attachment.FileCategory.DOCUMENT
                ),
            )
        except Exception as exc:
            logger.exception("Attachment DB create failed", exc_info=exc)
            # Attempt cleanup of saved file
            try:
                storage.delete(path)
            except Exception:
                pass
            raise serializers.ValidationError({"detail": _("Failed to create attachment record.")})
