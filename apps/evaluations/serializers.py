# apps/evaluations/serializers.py

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import Evaluation, EvaluationStatus, EvaluationTargetType

from apps.accounts.serializers import UserSerializer
from apps.cases.models import Case, CaseSession
from apps.appointments.models import Appointment


class EvaluationSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for displaying evaluation details.
    """

    evaluator = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)

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


class EvaluationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer used to create an evaluation.
    Only Supervisor / University Admin can create evaluations.
    """

    # Allow passing IDs directly from FE
    student_id = serializers.UUIDField(write_only=True, required=True)
    case_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    session_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    appointment_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Evaluation
        fields = [
            "student_id",
            "target_type",
            "case_id",
            "session_id",
            "appointment_id",
            "score",
            "rubric",
            "comment",
        ]

    # -------------------------
    # Validation helpers
    # -------------------------
    def validate_score(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(_("Score must be between 0 and 100."))
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if not user or not getattr(user, "role", None):
            raise serializers.ValidationError(_("User identification is required."))

        if user.role not in ["supervisor", "university_admin"]:
            raise serializers.ValidationError(_("Only supervisors or university admins can create evaluations."))

        target_type = attrs.get("target_type")

        # Resolve FK objects
        student_id = attrs.get("student_id")
        case_id = attrs.get("case_id")
        session_id = attrs.get("session_id")
        appointment_id = attrs.get("appointment_id")

        # -------------------------
        # Validate target mapping
        # -------------------------
        if target_type == EvaluationTargetType.CASE:
            if not case_id or session_id or appointment_id:
                raise serializers.ValidationError(
                    _("For target_type=case you must provide only case_id.")
                )
        elif target_type == EvaluationTargetType.SESSION:
            if not session_id or case_id or appointment_id:
                raise serializers.ValidationError(
                    _("For target_type=session you must provide only session_id.")
                )
        elif target_type == EvaluationTargetType.APPOINTMENT:
            if not appointment_id or case_id or session_id:
                raise serializers.ValidationError(
                    _("For target_type=appointment you must provide only appointment_id.")
                )
        else:
            raise serializers.ValidationError(_("Invalid target_type."))

        # -------------------------
        # Fetch objects
        # -------------------------
        from apps.accounts.models import User  # local import to avoid circular imports

        try:
            student = User.objects.get(id=student_id, role="student")
        except User.DoesNotExist:
            raise serializers.ValidationError({"student_id": _("Student not found.")})

        # University scope
        if getattr(student, "university_id", None) != getattr(user, "university_id", None):
            raise serializers.ValidationError(_("Student must belong to the same university."))

        # Target object resolution + integrity checks
        case = session = appointment = None

        if target_type == EvaluationTargetType.CASE:
            try:
                case = Case.objects.select_related("patient").get(id=case_id)
            except Case.DoesNotExist:
                raise serializers.ValidationError({"case_id": _("Case not found.")})

            # Basic integrity: student must match assigned student if your case has it
            # Adjust attribute name if different in your project (e.g., case.student / case.assigned_student)
            assigned_student = getattr(case, "student", None) or getattr(case, "assigned_student", None)
            if assigned_student and assigned_student != student:
                raise serializers.ValidationError(_("Student does not match the case assigned student."))

        if target_type == EvaluationTargetType.SESSION:
            try:
                session = CaseSession.objects.select_related("case").get(id=session_id)
            except CaseSession.DoesNotExist:
                raise serializers.ValidationError({"session_id": _("Session not found.")})

            assigned_student = getattr(session.case, "student", None) or getattr(session.case, "assigned_student", None)
            if assigned_student and assigned_student != student:
                raise serializers.ValidationError(_("Student does not match the session case assigned student."))

        if target_type == EvaluationTargetType.APPOINTMENT:
            try:
                appointment = Appointment.objects.select_related().get(id=appointment_id)
            except Appointment.DoesNotExist:
                raise serializers.ValidationError({"appointment_id": _("Appointment not found.")})

            # Adjust these fields according to your Appointment model:
            # some projects use appointment.student or appointment.user
            appt_student = getattr(appointment, "student", None) or getattr(appointment, "user", None)
            if appt_student and appt_student != student:
                raise serializers.ValidationError(_("Student does not match the appointment student."))

        # -------------------------
        # Prevent duplicates
        # -------------------------
        duplicate_qs = Evaluation.objects.filter(
            evaluator=user,
            student=student,
            target_type=target_type,
        )
        if target_type == EvaluationTargetType.CASE:
            duplicate_qs = duplicate_qs.filter(case=case)
        elif target_type == EvaluationTargetType.SESSION:
            duplicate_qs = duplicate_qs.filter(session=session)
        elif target_type == EvaluationTargetType.APPOINTMENT:
            duplicate_qs = duplicate_qs.filter(appointment=appointment)

        if duplicate_qs.exists():
            raise serializers.ValidationError(_("An evaluation already exists for this target by the same evaluator."))

        # Attach resolved objects to attrs for create()
        attrs["_student_obj"] = student
        attrs["_case_obj"] = case
        attrs["_session_obj"] = session
        attrs["_appointment_obj"] = appointment

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        # Pop helper objects
        student = validated_data.pop("_student_obj")
        case = validated_data.pop("_case_obj")
        session = validated_data.pop("_session_obj")
        appointment = validated_data.pop("_appointment_obj")

        # Remove incoming IDs
        validated_data.pop("student_id", None)
        validated_data.pop("case_id", None)
        validated_data.pop("session_id", None)
        validated_data.pop("appointment_id", None)

        evaluation = Evaluation.objects.create(
            university=user.university,
            evaluator=user,
            student=student,
            case=case,
            session=session,
            appointment=appointment,
            status=EvaluationStatus.DRAFT,
            **validated_data,
        )
        return evaluation


class EvaluationUpdateSerializer(serializers.ModelSerializer):
    """
    Update evaluation while respecting status rules.
    - Draft: can be updated
    - Submitted: optional restriction (here: allow comment/rubric/score by evaluator only)
    - Final: locked
    """

    class Meta:
        model = Evaluation
        fields = ["score", "rubric", "comment"]
        extra_kwargs = {
            "comment": {"required": False, "allow_blank": True},
            "rubric": {"required": False},
        }

    def validate_score(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(_("Score must be between 0 and 100."))
        return value

    def validate(self, attrs):
        instance: Evaluation = self.instance
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if instance.status == EvaluationStatus.FINAL:
            raise serializers.ValidationError(_("Final evaluations are locked and cannot be modified."))

        # Only evaluator (or university admin) can update
        if user and user.role not in ["supervisor", "university_admin"]:
            raise serializers.ValidationError(_("Not allowed."))

        # If you want to block updates when submitted, uncomment:
        # if instance.status == EvaluationStatus.SUBMITTED:
        #     raise serializers.ValidationError(_("Submitted evaluations cannot be edited."))

        return attrs


class EvaluationActionSerializer(serializers.Serializer):
    """
    Used for submit/finalize actions.
    """
    action = serializers.ChoiceField(choices=["submit", "finalize"])

    def validate(self, attrs):
        evaluation: Evaluation = self.context.get("evaluation")
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if evaluation.status == EvaluationStatus.FINAL:
            raise serializers.ValidationError(_("This evaluation is final and cannot be modified."))

        action = attrs["action"]
        if action == "submit":
            if user.role not in ["supervisor", "university_admin"]:
                raise serializers.ValidationError(_("Not allowed."))
        elif action == "finalize":
            if user.role not in ["supervisor", "university_admin"]:
                raise serializers.ValidationError(_("Not allowed."))

        return attrs

    def save(self, **kwargs):
        evaluation: Evaluation = self.context["evaluation"]
        action = self.validated_data["action"]

        if action == "submit":
            evaluation.status = EvaluationStatus.SUBMITTED
            evaluation.submitted_at = timezone.now()
            evaluation.save(update_fields=["status", "submitted_at", "updated_at"])

        elif action == "finalize":
            evaluation.status = EvaluationStatus.FINAL
            evaluation.finalized_at = timezone.now()
            evaluation.save(update_fields=["status", "finalized_at", "updated_at"])

        return evaluation
