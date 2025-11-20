from rest_framework import serializers
from .models import Attachment
from apps.accounts.serializers import UserSerializer


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for attachment data."""
    
    uploaded_by = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Attachment
        fields = [
            'id', 'file', 'original_filename', 'file_type', 'file_size',
            'mime_type', 'case_id', 'appointment_id', 'message_id',
            'content_id', 'uploaded_by', 'is_public', 'created_at', 'file_url'
        ]
        read_only_fields = ['id', 'file_size', 'mime_type', 'created_at']
    
    def get_file_url(self, obj):
        """Get file URL."""
        if obj.file:
            return obj.file.url
        return None


class AttachmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an attachment."""
    
    class Meta:
        model = Attachment
        fields = [
            'file', 'case_id', 'appointment_id', 'message_id',
            'content_id', 'is_public'
        ]
    
    def validate(self, data):
        """Validate attachment data."""
        file = data.get('file')
        
        if not file:
            raise serializers.ValidationError(("File is required"))
        
        # Check file size (limit to 10MB)
        if file.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(("File size exceeds 10MB limit"))
        
        return data
    
    def create(self, validated_data):
        """Create a new attachment."""
        file = validated_data.get('file')
        
        # Determine file type
        file_type = 'other'
        mime_type = file.content_type
        
        if mime_type.startswith('image/'):
            file_type = 'image'
        elif mime_type.startswith('video/'):
            file_type = 'video'
        elif mime_type.startswith('audio/'):
            file_type = 'audio'
        elif mime_type in [
            'application/pdf', 'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain'
        ]:
            file_type = 'document'
        
        # Create attachment
        attachment = Attachment.objects.create(
            file=file,
            original_filename=file.name,
            file_type=file_type,
            file_size=file.size,
            mime_type=mime_type,
            uploaded_by=self.context['request'].user,
            **validated_data
        )
        
        return attachment