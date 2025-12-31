from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from .models import Notification
from apps.accounts.models import User, Role
from apps.appointments.models import Appointment
from medismile.utils.auth import resolve_request_user


# ============================================================
# Minimal User Serializer (Notifications Scope Only)
# ============================================================
class NotificationUserSerializer(serializers.ModelSerializer):
    """
    Minimal, read-only user representation for notifications.
    Avoids coupling with accounts.serializers.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
        )
        read_only_fields = fields


# ============================================================
# Read Serializer (Inbox / Detail)
# ============================================================
class NotificationSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for notifications.
    Used for inbox, detail view, admin, audit.
    """

    sender = NotificationUserSerializer(read_only=True)
    recipient = NotificationUserSerializer(read_only=True)

    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()
    payload = serializers.JSONField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "sender",
            "recipient",
            "notification_type",
            "priority",
            "title",
            "message",
            "status",
            "response_message",
            "proposed_changes",
            "payload",
            "is_read",
            "read_at",
            "created_at",
            "updated_at",
            "target_type",
            "target_id",
        ]
        read_only_fields = fields

    def get_target_type(self, obj):
        return obj.target_content_type.model if obj.target_content_type else None

    def get_target_id(self, obj):
        return obj.target_object_id


# ============================================================
# Create Serializer
# ============================================================
class NotificationCreateSerializer(serializers.ModelSerializer):
    """
    Safe notification creation serializer.

    Supports:
    - Legacy appointment_id
    - Generic target (target_type + target_id)
    """

    appointment_id = serializers.UUIDField(write_only=True, required=False)

    target_type = serializers.CharField(
        write_only=True,
        required=False,
        help_text=_("Target model name (case, content, report, etc.)"),
    )
    target_id = serializers.UUIDField(write_only=True, required=False)
    payload = serializers.JSONField(write_only=True, required=False)

    recipient_id = serializers.UUIDField(write_only=True)
    sender_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            "notification_type",
            "priority",
            "appointment_id",
            "target_type",
            "target_id",
            "recipient_id",
            "sender_id",
            "title",
            "message",
            "proposed_changes",
            "payload",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        sender = resolve_request_user(request) if request else None

        # Sender must exist
        if not sender and not attrs.get("sender_id"):
            raise serializers.ValidationError(
                {"sender_id": _("Sender is required.")}
            )

        # Must reference something
        if not attrs.get("appointment_id") and not (
            attrs.get("target_type") and attrs.get("target_id")
        ):
            raise serializers.ValidationError(
                _("Notification must reference an appointment or a target object.")
            )

        # Role-based creation rules
        if sender:
            role = sender.role.name

            if role == Role.PATIENT:
                if attrs.get("notification_type") not in {
                    "appointment_update_request",
                    "appointment_cancel_request",
                }:
                    raise serializers.ValidationError(
                        _("Patients can only create appointment request notifications.")
                    )

            elif role == Role.STUDENT:
                # Student allowed (informational / appointment related)
                pass

            elif role in {
                Role.SUPERVISOR,
                Role.UNIVERSITY_ADMIN,
                Role.TECH_SUPPORT,
            }:
                pass

            else:
                raise serializers.ValidationError(
                    _("Your role is not allowed to create notifications.")
                )

        return attrs

    def create(self, validated_data):
        appointment_id = validated_data.pop("appointment_id", None)
        target_type = validated_data.pop("target_type", None)
        target_id = validated_data.pop("target_id", None)
        payload = validated_data.pop("payload", None)

        recipient_id = validated_data.pop("recipient_id")
        sender_id = validated_data.pop("sender_id", None)

        request = self.context.get("request")
        sender = resolve_request_user(request) if request else None
        if sender is None and sender_id:
            sender = User.objects.get(id=sender_id)

        recipient = User.objects.get(id=recipient_id)

        notification = Notification(
            sender=sender,
            recipient=recipient,
            **validated_data,
        )

        # Legacy appointment
        if appointment_id:
            notification.appointment = Appointment.objects.get(id=appointment_id)

        # Generic target
        if target_type and target_id:
            content_type = ContentType.objects.get(model=target_type.lower())
            notification.target_content_type = content_type
            notification.target_object_id = target_id

        if payload:
            notification.payload = payload

        notification.save()
        return notification


# ============================================================
# Update Serializer (Respond / Mark as Read)
# ============================================================
class NotificationUpdateSerializer(serializers.ModelSerializer):
    """
    Update notification:
    - Accept / Reject
    - Mark as read
    """

    class Meta:
        model = Notification
        fields = [
            "status",
            "response_message",
            "is_read",
        ]

    def validate(self, attrs):
        if "status" in attrs and attrs["status"] not in {
            "pending",
            "accepted",
            "rejected",
            "info",
        }:
            raise serializers.ValidationError(_("Invalid notification status."))
        return attrs
