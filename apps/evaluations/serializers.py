# apps/evaluations/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User, Role
from apps.appointments.models import Appointment
from apps.cases.models import Case, CaseSession

from .models import Evaluation, EvaluationAdjustment, EvaluationTargetType


class EvaluationAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationAdjustment
        fields = [
            "id",
            "adjusted_by",
            "adjusted_role",
            "old_score",
            "new_score",
            "reason",
            "adjusted_at",
        ]
        read_only_fields = fields


class EvaluationSerializer(serializers.ModelSerializer):
    original_score = serializers.IntegerField(source="score", read_only=True)
    adjustments = EvaluationAdjustmentSerializer(many=True, read_only=True)

    class Meta:
        model = Evaluation
        fields = [
            "id",
            "university",
            "evaluator",
            "evaluator_role",
            "student",
            "target_type",
            "target_id",
            "case",
            "session",
            "appointment",
            "status",
            "original_score",
            "final_score",
            "rubric",
            "comment",
            "submitted_at",
            "finalized_at",
            "created_at",
            "updated_at",
            "adjustments",
        ]
        read_only_fields = fields


class EvaluationCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=EvaluationTargetType.choices)
    target_id = serializers.UUIDField()
    original_score = serializers.IntegerField(min_value=0, max_value=100, required=False)
    score = serializers.IntegerField(min_value=0, max_value=100, required=False, write_only=True)
    rubric = serializers.JSONField(required=False)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if "original_score" not in attrs:
            if "score" in attrs:
                attrs["original_score"] = attrs.pop("score")
            else:
                raise serializers.ValidationError({"original_score": _("Original score is required.")})
        else:
            attrs.pop("score", None)

        target_type = attrs["target_type"]
        target_id = attrs["target_id"]

        case = session = appointment = None
        target_user = None

        if target_type == EvaluationTargetType.CASE:
            case = Case.objects.select_related("university", "student").filter(id=target_id).first()
            if not case:
                raise serializers.ValidationError({"target_id": _("Case not found.")})
        elif target_type == EvaluationTargetType.SESSION:
            session = (
                CaseSession.objects
                .select_related("case__university", "student")
                .filter(id=target_id)
                .first()
            )
            if not session:
                raise serializers.ValidationError({"target_id": _("Session not found.")})
            case = session.case
        elif target_type == EvaluationTargetType.APPOINTMENT:
            appointment = (
                Appointment.objects
                .select_related("case__university", "student", "patient")
                .filter(id=target_id)
                .first()
            )
            if not appointment:
                raise serializers.ValidationError({"target_id": _("Appointment not found.")})
            case = appointment.case
        elif target_type == EvaluationTargetType.STUDENT:
            target_user = User.objects.filter(id=target_id, role__name=Role.STUDENT).first()
            if not target_user:
                raise serializers.ValidationError({"target_id": _("Student not found.")})
        elif target_type == EvaluationTargetType.SUPERVISOR:
            target_user = User.objects.filter(id=target_id, role__name=Role.SUPERVISOR).first()
            if not target_user:
                raise serializers.ValidationError({"target_id": _("Supervisor not found.")})
        else:
            raise serializers.ValidationError({"target_type": _("Invalid target_type.")})

        attrs["case"] = case
        attrs["session"] = session
        attrs["appointment"] = appointment
        attrs["target_user"] = target_user
        attrs["score"] = attrs.pop("original_score")
        return attrs


class EvaluationAdjustSerializer(serializers.Serializer):
    new_score = serializers.IntegerField(min_value=0, max_value=100)
    reason = serializers.CharField()

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError(_("Adjustment reason is required."))
        return value


class EvaluationRatingSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    final_rating = serializers.FloatField(allow_null=True)
    total_evaluations = serializers.IntegerField()
    components = serializers.DictField()
