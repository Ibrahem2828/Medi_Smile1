# apps/reports/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Report
from apps.accounts.models import User, Role
from apps.universities.models import University
from apps.cases.models import Case


# ============================================================
# Read Serializer
# ============================================================

class ReportSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for reports.
    """

    student_name = serializers.SerializerMethodField()
    supervisor_name = serializers.SerializerMethodField()
    university_name = serializers.CharField(source="university.name", read_only=True)
    generated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "report_type",
            "case_id",
            "session_id",
            "title",
            "description",
            "content",
            "file_url",
            "attachments",
            "snapshot_data",
            "score",
            "feedback",
            "reviewed_at",
            "student",
            "student_name",
            "supervisor",
            "supervisor_name",
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

    def get_supervisor_name(self, obj):
        if not obj.supervisor:
            return None
        return obj.supervisor.get_full_name() or obj.supervisor.username

    def get_generated_by_name(self, obj):
        if not obj.generated_by:
            return None
        return obj.generated_by.get_full_name() or obj.generated_by.username


# ============================================================
# Create Serializers (Input Only)
# ============================================================

# Student submit report (clinical/media/session)
class ReportSubmitSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=[
        Report.ReportType.CLINICAL_CASE,
        Report.ReportType.SESSION_REPORT,
        Report.ReportType.MEDIA,
    ])
    case_id = serializers.UUIDField(required=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)
    attachments = serializers.JSONField(required=False)

    def validate(self, attrs):
        student = self.context["student"]
        try:
            case = Case.objects.get(id=attrs["case_id"], patient=student)
        except Case.DoesNotExist:
            raise serializers.ValidationError({"case_id": _("Case not found or not owned by student.")})

        attrs["case"] = case
        return attrs


# Generate report (supervisor/admin/tech)
class ReportGenerateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    report_type = serializers.ChoiceField(choices=Report.ReportType.choices)
    case_id = serializers.UUIDField(required=False, allow_null=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)
    file_url = serializers.CharField(required=False, allow_blank=True)
    attachments = serializers.JSONField(required=False)
    snapshot_data = serializers.JSONField(required=False)
    score = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=100)

    def validate(self, attrs):
        # Validate student
        try:
            student = User.objects.get(
                id=attrs["student_id"],
                role__name=Role.STUDENT,
            )
        except User.DoesNotExist:
            raise serializers.ValidationError({"student_id": _("Student not found or invalid role.")})

        # Infer university from student profile
        university = getattr(getattr(student, "studentprofile_profile", None), "university", None)
        if not university:
            raise serializers.ValidationError({"student_id": _("Student is not linked to a university.")})

        attrs["student"] = student
        attrs["university"] = university
        return attrs


class ReportReviewSerializer(serializers.Serializer):
    feedback = serializers.CharField(required=True, allow_blank=False)
    score = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=100)



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
