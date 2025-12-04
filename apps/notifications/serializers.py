from rest_framework import serializers
from .models import Notification
from apps.accounts.serializers import UserSerializer
from apps.appointments.serializers import AppointmentSerializer
from medismile.utils.auth import resolve_request_user


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notification data."""
    
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    appointment = AppointmentSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'sender', 'recipient', 'notification_type', 'appointment',
            'title', 'message', 'status', 'response_message', 'proposed_changes',
            'is_read', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a notification."""
    
    appointment_id = serializers.UUIDField(write_only=True)
    recipient_id = serializers.UUIDField(write_only=True)
    sender_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Notification
        fields = [
            'notification_type', 'appointment_id', 'recipient_id', 'sender_id',
            'title', 'message', 'proposed_changes'
        ]
    
    def create(self, validated_data):
        """Create a new notification."""
        appointment_id = validated_data.pop('appointment_id')
        recipient_id = validated_data.pop('recipient_id')
        sender_id = validated_data.pop('sender_id', None)
        
        # Get appointment
        from apps.appointments.models import Appointment
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Get recipient
        from apps.accounts.models import User
        recipient = User.objects.get(id=recipient_id)
        
        request = self.context.get('request')
        sender = resolve_request_user(request) if request else None
        if sender is None:
            if not sender_id:
                raise serializers.ValidationError({'sender_id': 'This field is required when authentication is disabled.'})
            sender = User.objects.get(id=sender_id)
        
        return Notification.objects.create(
            sender=sender,
            recipient=recipient,
            appointment=appointment,
            **validated_data
        )


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a notification (response)."""
    
    class Meta:
        model = Notification
        fields = ['status', 'response_message']
    
    def validate(self, data):
        """Validate notification update."""
        if 'status' in data and data['status'] not in ['accepted', 'rejected']:
            raise serializers.ValidationError("Status must be 'accepted' or 'rejected'")
        return data











