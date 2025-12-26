# apps/reports/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Report
from apps.accounts.models import User, Role
from apps.universities.models import University


# ============================================================
# Read Serializer
# ============================================================

class ReportSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for reports.
    """

    student_name = serializers.SerializerMethodField()
    university_name = serializers.CharField(source="university.name", read_only=True)
    generated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "report_type",
            "title",
            "description",
            "file_url",
            "snapshot_data",
            "student",
            "student_name",
            "university",
            "university_name",
            "generated_by",
            "generated_by_name",
            "is_active",
            "generated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    def get_generated_by_name(self, obj):
        if not obj.generated_by:
            return None
        return obj.generated_by.get_full_name() or obj.generated_by.username


# ============================================================
# Create Serializer (Input Only)
# ============================================================

class ReportCreateSerializer(serializers.Serializer):
    """
    Input serializer for generating a report.
    Actual creation handled by services.py
    """

    student_id = serializers.UUIDField()
    university_id = serializers.UUIDField()
    report_type = serializers.ChoiceField(choices=Report.ReportType.choices)
    title = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    file_url = serializers.CharField()
    snapshot_data = serializers.JSONField(required=False)

    def validate(self, attrs):
        # Validate student
        try:
            student = User.objects.get(
                id=attrs["student_id"],
                role__name=Role.STUDENT,
            )
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"student_id": _("Student not found or invalid role.")}
            )

        # Validate university
        try:
            university = University.objects.get(id=attrs["university_id"])
        except University.DoesNotExist:
            raise serializers.ValidationError(
                {"university_id": _("University not found.")}
            )

        attrs["student"] = student
        attrs["university"] = university
        return attrs


# ============================================================
# Visibility Update Serializer
# ============================================================

class ReportVisibilityUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for soft visibility toggle only.
    """

    class Meta:
        model = Report
        fields = ["is_active"]

    def validate(self, attrs):
        if "is_active" not in attrs:
            raise serializers.ValidationError(_("Only is_active can be updated."))
        return attrs
