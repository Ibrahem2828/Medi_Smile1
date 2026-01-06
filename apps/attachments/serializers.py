# apps/attachments/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from medismile.utils.auth import resolve_request_user

from apps.accounts.models import User, Role
from apps.appointments.models import Appointment
from .models import Attachment
from .storage_backends import get_storage_backend, generate_attachment_path


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
        # Guard empty file to avoid storage errors
        if not obj.file:
            return None
        storage = get_storage_backend()
        return storage.url(obj.file.name)


class AttachmentCreateSerializer(serializers.Serializer):
    appointment_id = serializers.UUIDField()
    file = serializers.FileField()
    attachment_type = serializers.ChoiceField(
        choices=Attachment.AttachmentType.choices
    )

    def validate(self, attrs):
        request = self.context["request"]
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

        path = generate_attachment_path(original_filename=file.name)

        storage.save(path, file)

        return Attachment.objects.create(
            appointment=validated_data["appointment"],
            case=validated_data["case"],
            uploaded_by=validated_data["uploaded_by"],
            file=path,
            original_filename=file.name,
            file_size=file.size,
            mime_type=file.content_type,
            attachment_type=validated_data["attachment_type"],
            file_category=(
                Attachment.FileCategory.IMAGE
                if file.content_type.startswith("image/")
                else Attachment.FileCategory.DOCUMENT
            ),
        )
    
