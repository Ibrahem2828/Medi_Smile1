from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from .models import Notification
from apps.accounts.models import User, Role
from apps.appointments.models import Appointment
from medismile.utils.scoping import get_user_university_id, same_university


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
        # The sender is always the authenticated caller. A client-supplied
        # sender_id is accepted only when it names the caller themself, so it
        # can never be used to impersonate another user.
        sender = getattr(request, "user", None) if request else None
        if not sender or not getattr(sender, "is_authenticated", False):
            raise serializers.ValidationError(
                {"sender_id": _("Sender is required.")}
            )
        sender_id = attrs.get("sender_id")
        if sender_id and str(sender_id) != str(sender.id):
            raise serializers.ValidationError(
                {"sender_id": _("You can only send notifications as yourself.")}
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

        try:
            recipient = User.objects.select_related("role").get(id=attrs["recipient_id"])
        except User.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"recipient_id": _("Invalid recipient id.")}
            ) from exc

        appointment = None
        if attrs.get("appointment_id"):
            try:
                appointment = Appointment.objects.get(id=attrs["appointment_id"])
            except Appointment.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"appointment_id": _("Invalid appointment id.")}
                ) from exc

        content_type = None
        target_type = attrs.get("target_type")
        if target_type and attrs.get("target_id"):
            content_type = ContentType.objects.filter(model=target_type.lower()).first()
            if content_type is None:
                raise serializers.ValidationError(
                    {"target_type": _("Invalid target type.")}
                )

        if not self._sender_may_notify(sender, recipient, appointment, content_type, attrs.get("target_id")):
            raise serializers.ValidationError(
                {"recipient_id": _("You are not allowed to notify this user.")}
            )

        attrs["_recipient"] = recipient
        attrs["_appointment"] = appointment
        attrs["_content_type"] = content_type
        return attrs

    # --------------------------------------------------------
    # Relationship rules (anti-spoofing)
    # --------------------------------------------------------
    @staticmethod
    def _participants(obj):
        return {
            pid
            for pid in (
                getattr(obj, "patient_id", None),
                getattr(obj, "student_id", None),
                getattr(obj, "supervisor_id", None),
            )
            if pid
        }

    @classmethod
    def _sender_may_notify(cls, sender, recipient, appointment, content_type, target_id) -> bool:
        """
        A sender may only notify users they have a real relationship with:
        - Tech Support: anyone (system operator).
        - Appointment-bound: both sides must be participants of the appointment.
        - Case-bound: both sides must be participants of the case, or the sender
          is the University Admin of the case's university.
        - Otherwise (staff only): sender and recipient share a university.
        Patients never get the "otherwise" branch.
        """
        from apps.cases.models import Case

        if sender.id == recipient.id:
            return False
        role = sender.role.name
        if role == Role.TECH_SUPPORT:
            return True

        if appointment is not None:
            participants = cls._participants(appointment)
            return sender.id in participants and recipient.id in participants

        if content_type is not None and content_type.model == "case":
            case = Case.objects.filter(id=target_id).first()
            if case is None:
                return False
            participants = cls._participants(case)
            if recipient.id not in participants and not same_university(recipient, case.university_id):
                return False
            if sender.id in participants:
                return True
            return role == Role.UNIVERSITY_ADMIN and same_university(sender, case.university_id)

        if role == Role.PATIENT:
            return False
        return same_university(sender, get_user_university_id(recipient))

    def create(self, validated_data):
        validated_data.pop("appointment_id", None)
        validated_data.pop("target_type", None)
        target_id = validated_data.pop("target_id", None)
        payload = validated_data.pop("payload", None)
        validated_data.pop("recipient_id")
        validated_data.pop("sender_id", None)

        recipient = validated_data.pop("_recipient")
        appointment = validated_data.pop("_appointment", None)
        content_type = validated_data.pop("_content_type", None)

        request = self.context.get("request")
        notification = Notification(
            sender=request.user,
            recipient=recipient,
            **validated_data,
        )

        # Legacy appointment
        if appointment is not None:
            notification.appointment = appointment

        # Generic target
        if content_type is not None and target_id:
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
