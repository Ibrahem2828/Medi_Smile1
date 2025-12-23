from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import SupportTicket, SupportTicketResponse

User = get_user_model()


# ============================================================
# Basic User Serializer (Lightweight)
# ============================================================

class UserBasicSerializer(serializers.ModelSerializer):
    """
    Lightweight user serializer for support context.
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "role",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return (f"{obj.first_name} {obj.last_name}").strip()


# ============================================================
# Support Ticket Response
# ============================================================

class SupportTicketResponseSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for ticket responses.
    """

    author = UserBasicSerializer(read_only=True)

    class Meta:
        model = SupportTicketResponse
        fields = [
            "id",
            "author",
            "message",
            "is_internal",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SupportTicketResponseCreateSerializer(serializers.ModelSerializer):
    """
    Create a response for a support ticket.
    """

    class Meta:
        model = SupportTicketResponse
        fields = [
            "message",
            "is_internal",
        ]
        extra_kwargs = {
            "is_internal": {"required": False, "default": False},
        }

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        if attrs.get("is_internal") and user.role != "tech_support":
            raise serializers.ValidationError(
                _("Only technical support can create internal responses.")
            )

        return attrs

    def create(self, validated_data):
        ticket: SupportTicket = self.context["ticket"]
        request = self.context.get("request")
        user = request.user

        # Auto-move ticket to in_progress if tech replies first
        if user.role == "tech_support" and ticket.status == SupportTicket.Status.OPEN:
            ticket.status = SupportTicket.Status.IN_PROGRESS
            ticket.save(update_fields=["status"])

        return SupportTicketResponse.objects.create(
            ticket=ticket,
            author=user,
            **validated_data,
        )


# ============================================================
# Support Ticket – Create
# ============================================================

class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """
    Create support ticket (any authenticated user).
    """

    class Meta:
        model = SupportTicket
        fields = [
            "category",
            "subject",
            "description",
            "priority",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        return SupportTicket.objects.create(
            created_by=user,
            **validated_data,
        )


# ============================================================
# Support Ticket – List
# ============================================================

class SupportTicketListSerializer(serializers.ModelSerializer):
    """
    List view for support tickets.
    """

    created_by = UserBasicSerializer(read_only=True)
    assigned_to = UserBasicSerializer(read_only=True)
    responses_count = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "created_by",
            "category",
            "subject",
            "priority",
            "status",
            "assigned_to",
            "responses_count",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        read_only_fields = fields

    def get_responses_count(self, obj):
        return obj.responses.count()


# ============================================================
# Support Ticket – Detail
# ============================================================

class SupportTicketDetailSerializer(serializers.ModelSerializer):
    """
    Detailed ticket view including responses.
    """

    created_by = UserBasicSerializer(read_only=True)
    assigned_to = UserBasicSerializer(read_only=True)
    responses = SupportTicketResponseSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "created_by",
            "category",
            "subject",
            "description",
            "priority",
            "status",
            "assigned_to",
            "resolution",
            "responses",
            "created_at",
            "updated_at",
            "resolved_at",
            "closed_at",
        ]
        read_only_fields = fields


# ============================================================
# Support Ticket – Update (Tech Support Only)
# ============================================================

class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    """
    Update support ticket (tech support only).
    """

    class Meta:
        model = SupportTicket
        fields = [
            "status",
            "priority",
            "assigned_to",
            "resolution",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user

        if user.role != "tech_support":
            raise serializers.ValidationError(
                _("Only technical support can update tickets.")
            )

        return attrs

    def update(self, instance, validated_data):
        new_status = validated_data.get("status")

        # Handle resolved timestamp
        if new_status == SupportTicket.Status.RESOLVED and instance.status != new_status:
            validated_data["resolved_at"] = timezone.now()

        # Handle closed timestamp
        if new_status == SupportTicket.Status.CLOSED and instance.status != new_status:
            validated_data["closed_at"] = timezone.now()

        return super().update(instance, validated_data)
