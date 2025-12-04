from rest_framework import serializers
from .models import Case, CaseHistory, CaseAssignmentRequest
from apps.accounts.serializers import UserSerializer
from apps.accounts.models import User
from medismile.utils.auth import resolve_request_user


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
    
    patient_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Case
        fields = [
            'title', 'description', 'priority', 'is_public', 'patient_id'
        ]
    
    def create(self, validated_data):
        """Create a new case."""
        patient_id = validated_data.pop('patient_id', None)
        request = self.context.get('request')
        request_user = resolve_request_user(request) if request else None
        
        patient = None
        if request_user and request_user.role == 'patient':
            patient = request_user
        elif patient_id:
            patient = User.objects.get(id=patient_id, role='patient')
        
        if not patient:
            raise serializers.ValidationError({
                'patient_id': 'Valid patient is required to create a case.'
            })
        
        validated_data['patient'] = patient
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
    
    student_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = CaseAssignmentRequest
        fields = [
            'case', 'message', 'student_id'
        ]
    
    def create(self, validated_data):
        """Create a new case assignment request."""
        student_id = validated_data.pop('student_id', None)
        request = self.context.get('request')
        request_user = resolve_request_user(request) if request else None
        
        student = None
        if request_user and request_user.role == 'student':
            student = request_user
        elif student_id:
            student = User.objects.get(id=student_id, role='student')
        
        if not student:
            raise serializers.ValidationError({
                'student_id': 'Valid student is required to request assignment.'
            })
        
        validated_data['student'] = student
        return super().create(validated_data)


class CaseAssignmentRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a case assignment request."""
    
    class Meta:
        model = CaseAssignmentRequest
        fields = [
            'status', 'supervisor_response'
        ]