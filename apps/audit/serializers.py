from rest_framework import serializers
from .models import AuditLog
from apps.accounts.serializers import UserSerializer


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit log data."""
    
    user = UserSerializer(read_only=True)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'action', 'description', 'content_type_name', 
            'object_id', 'additional_data', 'ip_address', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']