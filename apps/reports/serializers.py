# apps/reports/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    supervisor_name = serializers.SerializerMethodField()
    university_name = serializers.CharField(source="university.name", read_only=True)
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "report_type",
            "target_type",
            "target_id",
            "status",
            "title",
            "description",
            "content",
            "attachments",
            "snapshot_data",
            "score",
            "feedback",
            "review_notes",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "submitted_at",
            "rejected_at",
            "locked_at",
            "author",
            "author_role",
            "author_name",
            "student",
            "student_name",
            "supervisor",
            "supervisor_name",
            "university",
            "university_name",
            "file_url",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_author_name(self, obj):
        if not obj.author:
            return None
        return obj.author.get_full_name() or obj.author.username

    def get_student_name(self, obj):
        if not obj.student:
            return None
        return obj.student.get_full_name() or obj.student.username

    def get_supervisor_name(self, obj):
        if not obj.supervisor:
            return None
        return obj.supervisor.get_full_name() or obj.supervisor.username

    def get_approved_by_name(self, obj):
        if not obj.approved_by:
            return None
        return obj.approved_by.get_full_name() or obj.approved_by.username


class ReportCreateSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=Report.ReportType.choices)
    target_type = serializers.ChoiceField(choices=Report.TargetType.choices)
    target_id = serializers.UUIDField()
    title = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    content = serializers.JSONField(required=False)
    attachments = serializers.JSONField(required=False)
    case_id = serializers.UUIDField(required=False, allow_null=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    snapshot_data = serializers.JSONField(required=False)

    def validate_content(self, value):
        if value is None:
            return value
        if not isinstance(value, (dict, list)):
            raise serializers.ValidationError(_("Content must be a JSON object or array."))
        return value


class ReportUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    content = serializers.JSONField(required=False)
    attachments = serializers.JSONField(required=False)

    def validate_content(self, value):
        if value is None:
            return value
        if not isinstance(value, (dict, list)):
            raise serializers.ValidationError(_("Content must be a JSON object or array."))
        return value


class ReportSubmitSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(required=False, default=True)


class ReportReviewSerializer(serializers.Serializer):
    review_notes = serializers.CharField(required=False, allow_blank=True)
    score = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=100)


class ReportRejectSerializer(serializers.Serializer):
    review_notes = serializers.CharField(required=True, allow_blank=False)


class ReportExportSerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=[("pdf", "PDF"), ("excel", "Excel"), ("csv", "CSV")])
