from rest_framework import serializers

from .models import AuditLog
from apps.accounts.models import User


# ============================================================
# Minimal User Serializer (Audit Scope)
# ============================================================
class AuditUserSerializer(serializers.ModelSerializer):
    """
    Minimal, read-only user representation for audit logs.
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
# Audit Log Serializer
# ============================================================
class AuditLogSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for audit logs.
    Used by:
    - Audit dashboard
    - IT Support
    - University Admin (scoped)
    """

    actor = AuditUserSerializer(source="user", read_only=True)
    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )
    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor",
            "university_name",
            "action",
            "description",
            "target_type",
            "target_id",
            "metadata",
            "ip_address",
            "user_agent",
            "created_at",
        )
        read_only_fields = fields

    # =========================
    # Generic Target Helpers
    # =========================

    def get_target_type(self, obj):
        if obj.content_type:
            return obj.content_type.model
        return None

    def get_target_id(self, obj):
        return obj.object_id
