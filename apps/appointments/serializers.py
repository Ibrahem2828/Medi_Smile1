from rest_framework import serializers
from .models import Appointment
from apps.accounts.serializers import UserSerializer
from apps.cases.serializers import CaseSerializer


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for appointment data."""
    
    patient = UserSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    case = CaseSerializer(read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'user', 'case', 'appointment_date',
            'status', 'is_archived', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an appointment."""
    
    patient_id = serializers.UUIDField(write_only=True)
    user_id = serializers.UUIDField(write_only=True)
    case_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Appointment
        fields = [
            'patient_id', 'user_id', 'case_id', 'appointment_date', 'status'
        ]
    
    def create(self, validated_data):
        """Create a new appointment."""
        patient_id = validated_data.pop('patient_id')
        user_id = validated_data.pop('user_id')
        case_id = validated_data.pop('case_id', None)
        
        # Get patient
        from apps.accounts.models import User
        patient = User.objects.get(id=patient_id, role='patient')
        user = User.objects.get(id=user_id)
        
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