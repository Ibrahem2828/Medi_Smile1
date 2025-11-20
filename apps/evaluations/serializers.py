from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Evaluation
from apps.accounts.serializers import UserSerializer
from apps.appointments.serializers import AppointmentSerializer


class EvaluationSerializer(serializers.ModelSerializer):
    """Serializer for evaluation data."""
    
    patient = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    appointment = AppointmentSerializer(read_only=True)
    
    class Meta:
        model = Evaluation
        fields = [
            'id', 'patient', 'student', 'appointment',
            'rating', 'comment', 'evaluator_type', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EvaluationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an evaluation."""
    
    patient_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    student_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    appointment_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Evaluation
        fields = [
            'patient_id', 'student_id', 'appointment_id',
            'rating', 'comment', 'evaluator_type'
        ]
    
    def validate(self, data):
        """Validate evaluation data based on evaluator type and business rules."""
        from django.utils.translation import gettext_lazy as _
        
        rating = data.get('rating')
        if rating is None or rating < 1 or rating > 10:
            raise serializers.ValidationError({'rating': _('Rating must be between 1 and 10')})
        
        evaluator_type = data.get('evaluator_type')
        user = self.context['request'].user
        
        # Validate evaluator type matches user role
        if evaluator_type == 'patient' and user.role != 'patient':
            raise serializers.ValidationError({'evaluator_type': _('Only patients can create patient evaluations')})
        elif evaluator_type == 'supervisor' and user.role != 'supervisor':
            raise serializers.ValidationError({'evaluator_type': _('Only supervisors can create supervisor evaluations')})
        elif evaluator_type == 'student' and user.role != 'student':
            raise serializers.ValidationError({'evaluator_type': _('Only students can create student evaluations')})
        elif evaluator_type == 'university' and user.role != 'university_admin':
            raise serializers.ValidationError({'evaluator_type': _('Only university admins can create university evaluations')})
        elif evaluator_type == 'admin' and user.role not in ['university_admin', 'tech_support']:
            raise serializers.ValidationError({'evaluator_type': _('Only admins can create admin dashboard evaluations')})
        
        # Business rules validation
        patient_id = data.get('patient_id')
        student_id = data.get('student_id')
        
        # Rule: No one evaluates patients (patient_id should not be set when creating evaluation)
        # Patients are never evaluated, so patient_id is only for tracking which patient gave the evaluation
        
        # Rule: Supervisor evaluates student
        if evaluator_type == 'supervisor':
            if not student_id:
                raise serializers.ValidationError({'student_id': _('Supervisor must evaluate a student')})
        
        # Rule: Patient evaluates student or clinic
        # Note: Clinic evaluation can be done without student_id (clinic info in comment)
        if evaluator_type == 'patient':
            # Patient can evaluate student (with student_id) or clinic (without student_id, info in comment)
            pass
        
        # Rule: Student evaluates college or clinic
        if evaluator_type == 'student':
            # Student evaluates college/clinic - no student_id required
            # College/clinic information can be stored in comment field
            pass
        
        # Rule: University evaluates student academic performance
        if evaluator_type == 'university':
            if not student_id:
                raise serializers.ValidationError({'student_id': _('University must evaluate a student')})
        
        # Rule: Admin evaluates admin dashboard
        if evaluator_type == 'admin':
            # Admin dashboard evaluation - no specific entity required
            pass
        
        return data
    
    def create(self, validated_data):
        """Create a new evaluation."""
        user = self.context['request'].user
        evaluator_type = validated_data.get('evaluator_type')
        
        patient_id = validated_data.pop('patient_id', None)
        student_id = validated_data.pop('student_id', None)
        appointment_id = validated_data.pop('appointment_id', None)
        
        from apps.accounts.models import User
        
        # Auto-set patient_id if evaluator is a patient
        patient = None
        if evaluator_type == 'patient' and user.role == 'patient':
            # Patient is evaluating, so set patient to the current user
            patient = user
        elif patient_id:
            patient = User.objects.get(id=patient_id, role='patient')
        
        student = None
        if student_id:
            student = User.objects.get(id=student_id, role='student')
        
        appointment = None
        if appointment_id:
            from apps.appointments.models import Appointment
            appointment = Appointment.objects.get(id=appointment_id)
            # Validate appointment relationships
            if patient and appointment.patient != patient:
                raise serializers.ValidationError({'patient_id': _('Patient does not match the appointment')})
            if student and appointment.user != student:
                raise serializers.ValidationError({'student_id': _('Student does not match the appointment')})
        
        return Evaluation.objects.create(
            patient=patient,
            student=student,
            appointment=appointment,
            **validated_data
        )