from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SupportTicket, SupportTicketResponse

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for ticket display."""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'full_name', 'role']
        read_only_fields = fields
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class SupportTicketResponseSerializer(serializers.ModelSerializer):
    """Serializer for support ticket responses."""
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = SupportTicketResponse
        fields = ['id', 'ticket', 'user', 'message', 'is_internal', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a support ticket."""
    
    class Meta:
        model = SupportTicket
        fields = ['category', 'subject', 'message', 'priority']
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class SupportTicketListSerializer(serializers.ModelSerializer):
    """Serializer for listing support tickets."""
    user = UserBasicSerializer(read_only=True)
    assigned_to = UserBasicSerializer(read_only=True)
    response_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'user', 'category', 'subject', 'priority', 'status',
            'assigned_to', 'response_count', 'created_at', 'updated_at', 'resolved_at'
        ]
        read_only_fields = fields
    
    def get_response_count(self, obj):
        return obj.responses.count()


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    """Serializer for support ticket details with responses."""
    user = UserBasicSerializer(read_only=True)
    assigned_to = UserBasicSerializer(read_only=True)
    responses = SupportTicketResponseSerializer(many=True, read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'user', 'category', 'subject', 'message', 'priority',
            'status', 'assigned_to', 'resolution', 'responses',
            'created_at', 'updated_at', 'resolved_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a support ticket (admin/tech support only)."""
    
    class Meta:
        model = SupportTicket
        fields = ['status', 'priority', 'assigned_to', 'resolution']
    
    def update(self, instance, validated_data):
        # If status is changed to resolved, set resolved_at
        if 'status' in validated_data:
            if validated_data['status'] == 'resolved' and instance.status != 'resolved':
                from django.utils import timezone
                validated_data['resolved_at'] = timezone.now()
            elif validated_data['status'] != 'resolved':
                validated_data['resolved_at'] = None
        
        return super().update(instance, validated_data)


class SupportTicketResponseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a response to a support ticket."""
    
    class Meta:
        model = SupportTicketResponse
        fields = ['message', 'is_internal']
        extra_kwargs = {
            'is_internal': {'default': False}
        }
    
    def create(self, validated_data):
        ticket = self.context['ticket']
        user = self.context['request'].user
        validated_data['ticket'] = ticket
        validated_data['user'] = user
        
        # Only tech support can create internal notes
        if validated_data.get('is_internal', False) and user.role != 'tech_support':
            validated_data['is_internal'] = False
        
        # Update ticket status if it's a new response from tech support
        if user.role == 'tech_support' and ticket.status == 'open':
            ticket.status = 'in_progress'
            ticket.save()
        
        return super().create(validated_data)

