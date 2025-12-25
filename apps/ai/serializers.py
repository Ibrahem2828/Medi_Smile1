from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import AIDiagnosis
from apps.accounts.serializers import UserSerializer
from apps.cases.serializers import CaseSerializer


# ============================================================
# READ SERIALIZER (AI DIAGNOSIS RESPONSE)
# ============================================================

class AIDiagnosisSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for AI diagnosis results.

    This serializer returns a FULL, unified diagnosis report,
    including:
    - Primary diagnosis
    - All detected findings
    - Detailed patient-safe report
    """

    case = CaseSerializer(read_only=True)
    patient = UserSerializer(read_only=True)
    requested_by = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)

    class Meta:
        model = AIDiagnosis
        fields = [
            # Identifiers
            "id",
            "created_at",
            "status",

            # Context
            "case",
            "patient",
            "requested_by",

            # Input
            "raw_symptoms",
            "normalized_symptoms",

            # Headline diagnosis
            "primary_diagnosis",

            # Detailed findings
            "detected_findings",

            # Narrative report
            "patient_explanation",
            "report_text",

            # Risk assessment
            "confidence_level",
            "severity_level",
            "urgency_level",

            # Guidance
            "recommendations",

            # Review
            "reviewed_by",
            "reviewed_at",

            # Internal metadata (may be hidden in UI if needed)
            "ai_metadata",
        ]

        read_only_fields = fields


# ============================================================
# CREATE / REQUEST SERIALIZER (AI REQUEST INPUT)
# ============================================================

class AIDiagnosisRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting an AI diagnosis.

    Input may include:
    - Symptoms text (required)
    - Dental images (optional, handled in views)
    """

    case_id = serializers.UUIDField(
        required=True,
        help_text=_("Related clinical case ID"),
    )

    symptoms_text = serializers.CharField(
        required=True,
        min_length=10,
        help_text=_(
            "Patient symptoms description "
            "(text or speech-to-text output)"
        ),
    )

    def validate_symptoms_text(self, value: str) -> str:
        """
        Ensure symptoms text is meaningful enough for AI analysis.
        """
        word_count = len(value.split())
        if word_count < 3:
            raise serializers.ValidationError(
                _("Symptoms description is too short for meaningful analysis.")
            )
        return value
