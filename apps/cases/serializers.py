from rest_framework import serializers
from .models import Case, CaseHistory, CaseAssignmentRequest
from apps.accounts.serializers import UserSerializer


class CaseHistorySerializer(serializers.ModelSerializer):
    """Serializer for case history data."""
    
    performed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = CaseHistory
        fields = [
            'id', 'action', 'description', 'performed_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CaseAssignmentRequestSerializer(serializers.ModelSerializer):
    """Serializer for case assignment request data."""
    
    student = UserSerializer(read_only=True)
    
    class Meta:
        model = CaseAssignmentRequest
        fields = [
            'id', 'case', 'student', 'message', 'status', 
            'supervisor_response', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CaseSerializer(serializers.ModelSerializer):
    """Serializer for case data."""
    
    patient = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    supervisor = UserSerializer(read_only=True)
    history = CaseHistorySerializer(many=True, read_only=True)
    assignment_requests = CaseAssignmentRequestSerializer(many=True, read_only=True)
    
    class Meta:
        model = Case
        fields = [
            'id', 'title', 'description', 'patient', 'student', 
            'supervisor', 'status', 'priority', 'is_public', 
            'created_at', 'updated_at', 'history', 'assignment_requests'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CaseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a case."""
    
    class Meta:
        model = Case
        fields = [
            'title', 'description', 'priority', 'is_public'
        ]
    
    def create(self, validated_data):
        """Create a new case."""
        validated_data['patient'] = self.context['request'].user
        return super().create(validated_data)


class CaseUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a case."""
    
    class Meta:
        model = Case
        fields = [
            'title', 'description', 'status', 'priority', 'is_public'
        ]


class CaseAssignmentRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a case assignment request."""
    
    class Meta:
        model = CaseAssignmentRequest
        fields = [
            'case', 'message'
        ]
    
    def create(self, validated_data):
        """Create a new case assignment request."""
        validated_data['student'] = self.context['request'].user
        return super().create(validated_data)


class CaseAssignmentRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a case assignment request."""
    
    class Meta:
        model = CaseAssignmentRequest
        fields = [
            'status', 'supervisor_response'
        ]