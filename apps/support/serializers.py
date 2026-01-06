# apps/support/serializers.py
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import Role
from .models import SupportTicket, SupportTicketResponse

User = get_user_model()


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _role_name(user) -> str | None:
    role = getattr(user, "role", None)
    return getattr(role, "name", None)


# ------------------------------------------------------------
# User (Light)
# ------------------------------------------------------------

class UserBasicSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "username", "first_name", "last_name", "full_name", "role_name")
        read_only_fields = fields

    def get_full_name(self, obj):
        return (f"{obj.first_name} {obj.last_name}").strip()

    def get_role_name(self, obj):
        return _role_name(obj)


# ------------------------------------------------------------
# Responses
# ------------------------------------------------------------

class SupportTicketResponseSerializer(serializers.ModelSerializer):
    author = UserBasicSerializer(read_only=True)

    class Meta:
        model = SupportTicketResponse
        fields = ("id", "author", "message", "is_internal", "created_at", "updated_at")
        read_only_fields = fields


class SupportTicketResponseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicketResponse
        fields = ("message", "is_internal")
        extra_kwargs = {"is_internal": {"required": False, "default": False}}

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if attrs.get("is_internal") and _role_name(user) != Role.TECH_SUPPORT:
            raise serializers.ValidationError(_("Only technical support can create internal notes."))

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        ticket: SupportTicket = self.context["ticket"]

        # If tech replies and ticket is OPEN -> move to IN_PROGRESS
        if _role_name(user) == Role.TECH_SUPPORT and ticket.status == SupportTicket.Status.OPEN:
            ticket.status = SupportTicket.Status.IN_PROGRESS
            ticket.save(update_fields=["status", "updated_at"])

        return SupportTicketResponse.objects.create(
            ticket=ticket,
            author=user,
            **validated_data,
        )


# ------------------------------------------------------------
# Tickets
# ------------------------------------------------------------

class SupportTicketCreateSerializer(serializers.ModelSerializer):
    # Override to allow alias values before we normalize/validate.
    category = serializers.CharField()
    priority = serializers.CharField()

    class Meta:
        model = SupportTicket
        fields = ("category", "subject", "description", "priority", "related_app")

    def validate(self, attrs):
        # Normalize and alias priority/category to reduce client-side errors.
        category = (attrs.get("category") or "").strip().lower()
        priority = (attrs.get("priority") or "").strip().lower()

        # Fallback defaults if missing
        if not category:
            category = SupportTicket.Category.TECHNICAL
        if not priority:
            priority = SupportTicket.Priority.MEDIUM

        # Allow common aliases (non-fatal: fallback to medium/technical)
        priority_aliases = {
            "high": SupportTicket.Priority.URGENT,
            "normal": SupportTicket.Priority.MEDIUM,
            "medium": SupportTicket.Priority.MEDIUM,
            "urgent": SupportTicket.Priority.URGENT,
            "low": SupportTicket.Priority.LOW,
        }
        attrs["priority"] = priority_aliases.get(priority, SupportTicket.Priority.MEDIUM)

        category_choices = dict(SupportTicket.Category.choices)
        attrs["category"] = category if category in category_choices else SupportTicket.Category.OTHER

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        try:
            return SupportTicket.objects.create(created_by=user, **validated_data)
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
            raise serializers.ValidationError(detail)


class SupportTicketListSerializer(serializers.ModelSerializer):
    created_by = UserBasicSerializer(read_only=True)
    assigned_to = UserBasicSerializer(read_only=True)
    responses_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SupportTicket
        fields = (
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
            "closed_at",
        )
        read_only_fields = fields


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    created_by = UserBasicSerializer(read_only=True)
    assigned_to = UserBasicSerializer(read_only=True)
    responses = SupportTicketResponseSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "created_by",
            "category",
            "related_app",
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
        )
        read_only_fields = fields


class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    """
    Tech Support: can update everything (status/priority/assigned_to/resolution)
    University Admin: can update limited fields (status/priority) within university scope
    """

    class Meta:
        model = SupportTicket
        fields = ("status", "priority", "assigned_to", "resolution")

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        role = _role_name(user)

        if role not in {Role.TECH_SUPPORT, Role.UNIVERSITY_ADMIN}:
            raise serializers.ValidationError(_("You are not allowed to update tickets."))

        # University Admin محدود
        if role == Role.UNIVERSITY_ADMIN:
            if "assigned_to" in attrs or "resolution" in attrs:
                raise serializers.ValidationError(_("University admin can only update status/priority."))

        new_status = attrs.get("status")
        new_resolution = attrs.get("resolution")

        if new_status == SupportTicket.Status.RESOLVED:
            if not (new_resolution or getattr(self.instance, "resolution", None)):
                raise serializers.ValidationError(_("Resolved tickets must include a resolution."))

        return attrs

    def update(self, instance, validated_data):
        new_status = validated_data.get("status")

        if new_status == SupportTicket.Status.RESOLVED and instance.status != new_status:
            validated_data.setdefault("resolved_at", timezone.now())

        if new_status == SupportTicket.Status.CLOSED and instance.status != new_status:
            validated_data.setdefault("closed_at", timezone.now())
            if not instance.resolved_at and (validated_data.get("resolution") or instance.resolution):
                validated_data.setdefault("resolved_at", timezone.now())

        return super().update(instance, validated_data)
