# apps/evaluations/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User, Role
from apps.cases.models import Case, CaseSession
from apps.appointments.models import Appointment

from .models import Evaluation, EvaluationStatus, EvaluationTargetType


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = [
            "id",
            "university",
            "evaluator",
            "student",
            "target_type",
            "case",
            "session",
            "appointment",
            "status",
            "score",
            "rubric",
            "comment",
            "submitted_at",
            "finalized_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class EvaluationCreateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    target_type = serializers.ChoiceField(choices=EvaluationTargetType.choices)

    case_id = serializers.UUIDField(required=False, allow_null=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    appointment_id = serializers.UUIDField(required=False, allow_null=True)

    score = serializers.IntegerField(min_value=0, max_value=100)
    rubric = serializers.JSONField(required=False)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # Resolve student
        try:
            student = User.objects.get(id=attrs["student_id"], role__name=Role.STUDENT)
        except User.DoesNotExist:
            raise serializers.ValidationError({"student_id": _("Student not found.")})

        target_type = attrs["target_type"]

        case = session = appointment = None

        def _reject(msg):
            raise serializers.ValidationError(msg)

        if target_type == EvaluationTargetType.CASE:
            if not attrs.get("case_id") or attrs.get("session_id") or attrs.get("appointment_id"):
                _reject(_("For target_type=case provide only case_id."))
            try:
                case = Case.objects.select_related("university").get(id=attrs["case_id"])
            except Case.DoesNotExist:
                raise serializers.ValidationError({"case_id": _("Case not found.")})
        elif target_type == EvaluationTargetType.SESSION:
            if not attrs.get("session_id") or attrs.get("case_id") or attrs.get("appointment_id"):
                _reject(_("For target_type=session provide only session_id."))
            try:
                session = CaseSession.objects.select_related("case__university").get(id=attrs["session_id"])
            except CaseSession.DoesNotExist:
                raise serializers.ValidationError({"session_id": _("Session not found.")})
            case = session.case
        elif target_type == EvaluationTargetType.APPOINTMENT:
            if not attrs.get("appointment_id") or attrs.get("case_id") or attrs.get("session_id"):
                _reject(_("For target_type=appointment provide only appointment_id."))
            try:
                appointment = Appointment.objects.select_related().get(id=attrs["appointment_id"])
            except Appointment.DoesNotExist:
                raise serializers.ValidationError({"appointment_id": _("Appointment not found.")})
            # best-effort mapping to case/university if your appointment has case
            case = getattr(appointment, "case", None)
        else:
            _reject(_("Invalid target_type."))

        # University scope resolution:
        # prefer case.university if available, else student's university
        university = getattr(case, "university", None) if case else getattr(student, "university", None)
        if not university:
            raise serializers.ValidationError(_("University could not be resolved for this evaluation."))

        attrs["student"] = student
        attrs["case"] = case if target_type == EvaluationTargetType.CASE else None
        attrs["session"] = session if target_type == EvaluationTargetType.SESSION else None
        attrs["appointment"] = appointment if target_type == EvaluationTargetType.APPOINTMENT else None
        attrs["university"] = university

        return attrs


class EvaluationUpdateSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=0, max_value=100, required=False)
    rubric = serializers.JSONField(required=False)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(_("No fields to update."))
        return attrs
