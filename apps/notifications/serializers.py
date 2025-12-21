from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from .models import Notification
from apps.accounts.serializers import UserSerializer
from apps.appointments.serializers import AppointmentSerializer
from medismile.utils.auth import resolve_request_user


# ============================================================
# Read Serializer (Inbox / Detail)
# ============================================================

class NotificationSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for notifications.

    Used for:
    - Inbox
    - Detail view
    - Admin / audit
    """

    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    appointment = AppointmentSerializer(read_only=True)

    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'sender',
            'recipient',
            'notification_type',
            'priority',
            'appointment',
            'target_type',
            'target_id',
            'title',
            'message',
            'status',
            'response_message',
            'proposed_changes',
            'is_read',
            'read_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_target_type(self, obj):
        if obj.target_content_type:
            return obj.target_content_type.model
        return None

    def get_target_id(self, obj):
        return obj.target_object_id


# ============================================================
# Create Serializer
# ============================================================

class NotificationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating notifications.

    Supports:
    - Appointment-based notifications (legacy)
    - Generic target notifications (case / session / content)
    """

    # --- Legacy / Backward compatible ---
    appointment_id = serializers.UUIDField(write_only=True, required=False)

    # --- Generic Target ---
    target_type = serializers.CharField(
        write_only=True,
        required=False,
        help_text=_("Model name of the target (case, casesession, content, etc.)")
    )
    target_id = serializers.UUIDField(write_only=True, required=False)

    # --- Users ---
    recipient_id = serializers.UUIDField(write_only=True)
    sender_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            'notification_type',
            'priority',
            'appointment_id',
            'target_type',
            'target_id',
            'recipient_id',
            'sender_id',
            'title',
            'message',
            'proposed_changes',
        ]

    def validate(self, attrs):
        request = self.context.get('request')
        sender = resolve_request_user(request) if request else None

        if not sender and not attrs.get('sender_id'):
            raise serializers.ValidationError(
                {'sender_id': _('Sender is required when authentication is disabled.')}
            )

        # Must reference something (appointment OR generic target)
        if not attrs.get('appointment_id') and not (
            attrs.get('target_type') and attrs.get('target_id')
        ):
            raise serializers.ValidationError(
                _('Notification must reference an appointment or a target object.')
            )

        return attrs

    def create(self, validated_data):
        from apps.accounts.models import User
        from apps.appointments.models import Appointment

        appointment_id = validated_data.pop('appointment_id', None)
        target_type = validated_data.pop('target_type', None)
        target_id = validated_data.pop('target_id', None)

        recipient_id = validated_data.pop('recipient_id')
        sender_id = validated_data.pop('sender_id', None)

        # Resolve sender
        request = self.context.get('request')
        sender = resolve_request_user(request) if request else None
        if sender is None and sender_id:
            sender = User.objects.get(id=sender_id)

        recipient = User.objects.get(id=recipient_id)

        notification = Notification(
            sender=sender,
            recipient=recipient,
            **validated_data
        )

        # Legacy appointment support
        if appointment_id:
            notification.appointment = Appointment.objects.get(id=appointment_id)

        # Generic target support
        if target_type and target_id:
            content_type = ContentType.objects.get(model=target_type.lower())
            notification.target_content_type = content_type
            notification.target_object_id = target_id

        notification.save()
        return notification


# ============================================================
# Update Serializer (Respond / Mark)
# ============================================================

class NotificationUpdateSerializer(serializers.ModelSerializer):
    """
    Update notification:
    - Accept / Reject requests
    - Mark as read
    """

    class Meta:
        model = Notification
        fields = [
            'status',
            'response_message',
            'is_read',
        ]

    def validate(self, attrs):
        if 'status' in attrs:
            if attrs['status'] not in ['accepted', 'rejected', 'info']:
                raise serializers.ValidationError(
                    _("Invalid notification status.")
                )
        return attrs
