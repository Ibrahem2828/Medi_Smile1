from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.cases.models import Case
from .models import Room, Message

User = get_user_model()


# ============================================================
# Minimal Public User Serializer (Messaging Scope)
# ============================================================
class MessagingUserSerializer(serializers.ModelSerializer):
    """
    Minimal, read-only user representation for messaging.
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
# Message Serializer
# ============================================================
class MessageSerializer(serializers.ModelSerializer):
    sender = MessagingUserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "content",
            "sent_at",
            "is_system",
        )
        read_only_fields = (
            "id",
            "sender",
            "sent_at",
            "is_system",
        )

    def validate_content(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty.")
        return value.strip()


# ============================================================
# Room Serializer
# ============================================================
class RoomSerializer(serializers.ModelSerializer):
    case = serializers.PrimaryKeyRelatedField(
        queryset=Case.objects.select_related(
            "patient",
            "student",
            "supervisor",
            "university",
        ),
    )
    participant_patient = MessagingUserSerializer(read_only=True)
    participant_student = MessagingUserSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = (
            "id",
            "case",
            "participant_patient",
            "participant_student",
            "created_at",
            "messages",
        )
        read_only_fields = (
            "id",
            "participant_patient",
            "participant_student",
            "created_at",
            "messages",
        )

    def validate_case(self, case: Case) -> Case:
        if not case.patient_id or not case.student_id:
            raise serializers.ValidationError("Case must have both patient and assigned student.")

        if case.status not in {
            Case.Status.ASSIGNED,
            Case.Status.IN_PROGRESS,
        }:
            raise serializers.ValidationError("Chat is available only for assigned / in-progress cases.")

        return case
