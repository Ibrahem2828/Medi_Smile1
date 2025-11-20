from rest_framework import serializers
from .models import AIDiagnosis
from apps.accounts.serializers import UserSerializer
from apps.cases.serializers import CaseSerializer


class AIDiagnosisSerializer(serializers.ModelSerializer):
    """Serializer for AI diagnosis data."""
    
    case = CaseSerializer(read_only=True)
    patient = UserSerializer(read_only=True)
    
    class Meta:
        model = AIDiagnosis
        fields = [
            'id', 'case', 'patient', 'symptoms', 'diagnosis', 
            'confidence_level', 'recommendations', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AIRequestSerializer(serializers.Serializer):
    """Serializer for AI analysis request."""
    
    symptoms = serializers.CharField(required=True)
    case_id = serializers.UUIDField(required=False)