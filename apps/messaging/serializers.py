from rest_framework import serializers
from django.conf import settings

from .models import Room, Message

User = settings.AUTH_USER_MODEL


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


# ============================================================
# Room Serializer
# ============================================================
class RoomSerializer(serializers.ModelSerializer):
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
        read_only_fields = fields
