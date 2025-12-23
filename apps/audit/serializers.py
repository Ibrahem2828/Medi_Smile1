# apps/audit/serializers.py

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import AuditLog
from apps.accounts.serializers import UserSerializer


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for audit log entries.
    """

    user = UserSerializer(read_only=True)
    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )

    content_type = serializers.CharField(
        source="content_type.model",
        read_only=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "university_name",
            "action",
            "description",
            "content_type",
            "object_id",
            "metadata",
            "ip_address",
            "user_agent",
            "created_at",
        ]
        read_only_fields = fields
