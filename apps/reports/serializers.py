from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Report
from apps.accounts.serializers import UserSerializer
from apps.universities.serializers import UniversitySerializer
from apps.accounts.models import User
from apps.universities.models import University
from medismile.utils.auth import resolve_request_user


# ============================================================
# Base / Read Serializer
# ============================================================

class ReportSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for reports.

    Reports are immutable records and cannot be edited once created.
    """

    student = UserSerializer(read_only=True)
    university = UniversitySerializer(read_only=True)
    generated_by = UserSerializer(read_only=True)

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
            "university",
            "generated_by",
            "is_active",
            "generated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


# ============================================================
# Create Serializer (Restricted)
# ============================================================

class ReportCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for generating a report.

    Rules:
    - Only supervisors / university_admin / tech_support can generate reports
    - Student cannot generate reports
    - Report is immutable after creation
    """

    student_id = serializers.UUIDField(write_only=True)
    university_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Report
        fields = [
            "student_id",
            "university_id",
            "report_type",
            "title",
            "description",
            "file_url",
            "snapshot_data",
            "is_active",
        ]

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    def validate(self, attrs):
        request = self.context.get("request")
        actor = resolve_request_user(request)

        if not actor:
            raise serializers.ValidationError(_("Authentication required."))

        if actor.role not in [
            "supervisor",
            "university_admin",
            "tech_support",
        ]:
            raise serializers.ValidationError(
                _("You are not allowed to generate reports.")
            )

        # Validate student
        try:
            student = User.objects.get(
                id=attrs["student_id"],
                role="student",
            )
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"student_id": _("Student not found.")}
            )

        # Validate university
        try:
            university = University.objects.get(
                id=attrs["university_id"]
            )
        except University.DoesNotExist:
            raise serializers.ValidationError(
                {"university_id": _("University not found.")}
            )

        # Optional: supervisor must belong to same university
        if actor.role == "supervisor":
            if hasattr(actor, "supervisorprofile"):
                if actor.supervisorprofile.university != university:
                    raise serializers.ValidationError(
                        _("You can only generate reports for your university.")
                    )

        attrs["student"] = student
        attrs["university"] = university
        attrs["generated_by"] = actor

        return attrs

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    def create(self, validated_data):
        validated_data.pop("student_id")
        validated_data.pop("university_id")

        return Report.objects.create(**validated_data)


# ============================================================
# Update Serializer (Soft Only)
# ============================================================

class ReportVisibilityUpdateSerializer(serializers.ModelSerializer):
    """
    Very limited update serializer.

    Only allows:
    - Soft visibility toggle (is_active)

    File, content, and metadata are immutable.
    """

    class Meta:
        model = Report
        fields = [
            "is_active",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        actor = resolve_request_user(request)

        if not actor:
            raise serializers.ValidationError(_("Authentication required."))

        if actor.role not in [
            "university_admin",
            "tech_support",
        ]:
            raise serializers.ValidationError(
                _("Only administrators can change report visibility.")
            )

        return attrs
