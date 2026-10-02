# apps/ai/serializers.py
from urllib.parse import urlparse

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import AIDiagnosis, AIImageUpload


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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        role = getattr(getattr(getattr(request, "user", None), "role", None), "name", None)
        if role == "patient":
            # Metadata contains raw service payloads, internal endpoints and
            # diagnostic audit data. A patient sees the deliberately prepared
            # patient-facing fields above, never this implementation detail.
            data.pop("ai_metadata", None)
        return data


MAX_IMAGES_PER_DIAGNOSIS = 5


class AIDiagnosisRequestSerializer(serializers.Serializer):
    """
    Input for ``POST /api/ai/diagnose/``.

    Images can be supplied in three ways (first match wins):
    1. multipart files under ``image`` / ``images`` / ``image_file`` (handled by the view);
    2. ``image_ids`` — ids returned by ``POST /api/ai/images/`` (preferred for JSON clients);
    3. ``image_urls`` — legacy; only hosts in ``AI_IMAGE_URL_ALLOWED_HOSTS`` are accepted
       (the backend fetches them, so an open list would be an SSRF hole).
    """

    symptoms_text = serializers.CharField(required=True, min_length=10, max_length=4000)
    patient_id = serializers.UUIDField(required=False, allow_null=True)
    image_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        max_length=MAX_IMAGES_PER_DIAGNOSIS,
        help_text=_("IDs returned by POST /api/ai/images/"),
    )
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
        max_length=MAX_IMAGES_PER_DIAGNOSIS,
        help_text=_("Legacy: image URLs on an allow-listed host (AI_IMAGE_URL_ALLOWED_HOSTS)"),
    )

    def validate_symptoms_text(self, value: str) -> str:
        if len(value.split()) < 3:
            raise serializers.ValidationError(_("Symptoms description is too short."))
        return value

    def validate_image_urls(self, value):
        allowed_hosts = {h.lower() for h in getattr(settings, "AI_IMAGE_URL_ALLOWED_HOSTS", []) if h}
        for url in value or []:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            if parsed.scheme != "https" or host not in allowed_hosts:
                raise serializers.ValidationError(
                    _("Image URLs from this host are not accepted. Upload the image via /api/ai/images/ instead.")
                )
        return value


class AIDiagnoseMultipartSerializer(serializers.Serializer):
    """Documentation-only: multipart form accepted by POST /api/ai/diagnose/."""

    symptoms_text = serializers.CharField(min_length=10, max_length=4000)
    image = serializers.FileField(required=False, help_text=_("Dental photo (JPEG/PNG/WebP, max 10 MB)"))
    image_ids = serializers.ListField(child=serializers.UUIDField(), required=False)


class AIDiagnoseResponseSerializer(serializers.Serializer):
    """Documentation-only: body returned by POST /api/ai/diagnose/ (201 and 503)."""

    diagnosis = AIDiagnosisSerializer()
    primary_suggestion = serializers.JSONField(allow_null=True)
    next_suggestion = serializers.JSONField(allow_null=True)
    all_suggestions = serializers.JSONField()
    detail = serializers.CharField(required=False, help_text=_("Present only on 503"))


class AIImageUploadCreateSerializer(serializers.Serializer):
    image = serializers.FileField(required=True, allow_empty_file=False)


class AIImageUploadSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = AIImageUpload
        fields = [
            "id",
            "content_type",
            "size_bytes",
            "width",
            "height",
            "sha256",
            "diagnosis",
            "file_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj) -> str:
        # Served through an authenticated view, not the public /media/ route.
        path = reverse("ai:ai-image-file", kwargs={"pk": obj.pk})
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


class AIDiagnosisReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField(required=False, default=True)
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500)
