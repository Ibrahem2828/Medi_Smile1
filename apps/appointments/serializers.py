from rest_framework import serializers
from .models import Appointment
from apps.accounts.serializers import UserSerializer
from apps.cases.serializers import CaseSerializer
from medismile.utils.auth import resolve_request_user


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for appointment data with null-safe nested serializers."""
    
    patient = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    case = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'user', 'case', 'appointment_date',
            'status', 'is_archived', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_patient(self, obj):
        if obj.patient:
            return UserSerializer(obj.patient).data
        return None
    
    def get_user(self, obj):
        if obj.user:
            return UserSerializer(obj.user).data
        return None
    
    def get_case(self, obj):
        if obj.case:
            return CaseSerializer(obj.case).data
        return None



class AppointmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an appointment."""
    
    patient_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    user_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    case_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Appointment
        fields = [
            'patient_id', 'user_id', 'case_id', 'appointment_date', 'status'
        ]
    
    def create(self, validated_data):
        """Create a new appointment."""
        patient_id = validated_data.pop('patient_id', None)
        user_id = validated_data.pop('user_id', None)
        case_id = validated_data.pop('case_id', None)
        
        # Get request and try to resolve user from alternative auth
        request = self.context.get('request')
        request_user = resolve_request_user(request) if request else None
        
        # Get patient - try from patient_id first (explicit), then from request_user
        from apps.accounts.models import User
        patient = None
        if patient_id:
            patient = User.objects.get(id=patient_id, role='patient')
        elif request_user and request_user.role == 'patient':
            patient = request_user
        
        if not patient:
            raise serializers.ValidationError({'patient_id': 'Valid patient is required'})
        
        # Get user (doctor/student) - try from user_id first (explicit), then from request_user
        user = None
        if user_id:
            user = User.objects.get(id=user_id)
        elif request_user and request_user.role in ['student', 'supervisor']:
            user = request_user
        
        if not user:
            raise serializers.ValidationError({'user_id': 'Valid user (doctor/student) is required'})
        
        # Get case if provided
        case = None
        if case_id:
            from apps.cases.models import Case
            case = Case.objects.get(id=case_id)
            # Validate case relationships
            if case.patient != patient:
                raise serializers.ValidationError({'patient_id': 'Patient does not match the case'})
        
        return Appointment.objects.create(
            patient=patient,
            user=user,
            case=case,
            **validated_data
        )


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an appointment."""
    
    class Meta:
        model = Appointment
        fields = [
            'appointment_date', 'status', 'is_archived', 'case'
        ]