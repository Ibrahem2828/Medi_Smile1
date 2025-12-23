# apps/attachments/serializers.py

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from django.db import transaction

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from medismile.utils.auth import resolve_request_user

from apps.cases.models import CaseSession
from .models import Attachment
from .storage_backends import (
    get_storage_backend,
    generate_attachment_path,
)


# ============================================================
# Read Serializer
# ============================================================

class AttachmentSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for attachments.
    Used by:
    - patient (read-only)
    - student
    - supervisor
    - admin / IT support
    """

    uploaded_by = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "attachment_type",
            "file_url",
            "original_filename",
            "file_size",
            "mime_type",
            "case_session",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        if not obj.file_path:
            return None

        storage = get_storage_backend()
        return storage.url(obj.file_path)


# ============================================================
# Create Serializer
# ============================================================

class AttachmentCreateSerializer(serializers.Serializer):
    """
    Create attachment (student only).

    Rules:
    - Must be linked to CaseSession
    - Only assigned student can upload
    - Session must NOT be approved
    """

    file = serializers.FileField()
    case_session_id = serializers.UUIDField()
    attachment_type = serializers.ChoiceField(
        choices=Attachment.AttachmentType.choices
    )

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)

        if not user:
            raise serializers.ValidationError(_("Authentication required."))

        if user.role != "student":
            raise serializers.ValidationError(_("Only students can upload attachments."))

        file = attrs.get("file")
        session_id = attrs.get("case_session_id")
        attachment_type = attrs.get("attachment_type")

        # ----------------------------
        # File validation
        # ----------------------------
        if not file:
            raise serializers.ValidationError(_("File is required."))

        max_size_mb = 10
        if file.size > max_size_mb * 1024 * 1024:
            raise serializers.ValidationError(
                _(f"File size exceeds {max_size_mb}MB limit.")
            )

        # ----------------------------
        # Session validation
        # ----------------------------
        try:
            session = (
                CaseSession.objects
                .select_related("case", "student")
                .get(id=session_id)
            )
        except CaseSession.DoesNotExist:
            raise serializers.ValidationError(
                {"case_session_id": _("Session not found.")}
            )

        if session.student != user:
            raise serializers.ValidationError(
                _("You are not assigned to this session.")
            )

        if session.status == CaseSession.Status.APPROVED:
            raise serializers.ValidationError(
                _("Attachments cannot be added after session approval.")
            )

        # ----------------------------
        # Before / After rules
        # ----------------------------
        if attachment_type == Attachment.AttachmentType.BEFORE_IMAGE:
            exists = Attachment.objects.filter(
                case_session=session,
                attachment_type=Attachment.AttachmentType.BEFORE_IMAGE,
            ).exists()
            if exists:
                raise serializers.ValidationError(
                    _("Before image already exists for this session.")
                )

        if attachment_type == Attachment.AttachmentType.AFTER_IMAGE:
            if not Attachment.objects.filter(
                case_session=session,
                attachment_type=Attachment.AttachmentType.BEFORE_IMAGE,
            ).exists():
                raise serializers.ValidationError(
                    _("Before image must be uploaded first.")
                )

        attrs["session"] = session
        attrs["user"] = user
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        file = validated_data["file"]
        session = validated_data["session"]
        user = validated_data["user"]
        attachment_type = validated_data["attachment_type"]

        # ----------------------------
        # Storage handling
        # ----------------------------
        storage = get_storage_backend()
        file_path = generate_attachment_path(
            original_filename=file.name,
            prefix="attachments/sessions",
        )

        storage.save(file_path, file)

        # ----------------------------
        # Create attachment record
        # ----------------------------
        attachment = Attachment.objects.create(
            case_session=session,
            attachment_type=attachment_type,
            file_path=file_path,
            original_filename=file.name,
            file_size=file.size,
            mime_type=file.content_type,
            uploaded_by=user,
        )

        return attachment
