# apps/ai/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import AIDiagnosis


class AIDiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIDiagnosis
        fields = [
            "id",
            "created_at",
            "updated_at",
            "status",
            "error_message",

            "case",
            "patient",
            "requested_by",

            "raw_symptoms",
            "normalized_symptoms",

            "diagnosis_label",
            "primary_diagnosis",
            "detected_findings",

            "patient_explanation",
            "report_text",
            "recommendations",

            "confidence_level",
            "severity_level",
            "urgency_level",

            "reviewed_by",
            "reviewed_at",

            "ai_metadata",
        ]
        read_only_fields = fields


class AIDiagnosisRequestSerializer(serializers.Serializer):
    case_id = serializers.UUIDField(required=True)
    symptoms_text = serializers.CharField(required=True, min_length=10)
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
        help_text=_("Optional image URLs already uploaded in attachments/storage"),
    )

    def validate_symptoms_text(self, value: str) -> str:
        if len(value.split()) < 3:
            raise serializers.ValidationError(_("Symptoms description is too short."))
        return value
