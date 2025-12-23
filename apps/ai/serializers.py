# apps/ai/serializers.py

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import AIDiagnosis
from apps.accounts.serializers import UserSerializer
from apps.cases.serializers import CaseSerializer


# ============================================================
# Read Serializer (Response)
# ============================================================

class AIDiagnosisSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for AI diagnosis results.
    """

    case = CaseSerializer(read_only=True)
    patient = UserSerializer(read_only=True)
    requested_by = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)

    class Meta:
        model = AIDiagnosis
        fields = [
            "id",
            "case",
            "patient",
            "requested_by",
            "raw_symptoms",
            "normalized_symptoms",
            "diagnosis_label",
            "confidence_level",
            "severity_level",
            "urgency_level",
            "patient_explanation",
            "recommendations",
            "ai_metadata",
            "status",
            "reviewed_by",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = fields


# ============================================================
# Create / Request Serializer (Input)
# ============================================================

class AIDiagnosisRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting AI symptom-based diagnosis.
    """

    case_id = serializers.UUIDField(
        required=True,
        help_text=_("Related clinical case ID"),
    )

    symptoms_text = serializers.CharField(
        required=True,
        min_length=10,
        help_text=_("Patient symptoms description (text or speech-to-text)"),
    )

    def validate_symptoms_text(self, value):
        if len(value.split()) < 3:
            raise serializers.ValidationError(
                _("Symptoms description is too short for meaningful analysis.")
            )
        return value
