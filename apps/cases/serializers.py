from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from .models import (
    Case,
    CaseHistory,
    CaseAssignmentRequest,
    CaseSession,
)
from apps.accounts.serializers import UserSerializer
from apps.accounts.models import User
from medismile.utils.auth import resolve_request_user


# ============================================================
# Case History (READ ONLY – Audit Trail)
# ============================================================

class CaseHistorySerializer(serializers.ModelSerializer):
    performed_by = UserSerializer(read_only=True)

    class Meta:
        model = CaseHistory
        fields = [
            "id",
            "action",
            "description",
            "performed_by",
            "created_at",
        ]
        read_only_fields = fields


# ============================================================
# Case Assignment Requests
# ============================================================

class CaseAssignmentRequestSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)

    class Meta:
        model = CaseAssignmentRequest
        fields = [
            "id",
            "case",
            "student",
            "message",
            "status",
            "supervisor_response",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "status",
            "supervisor_response",
            "created_at",
            "updated_at",
        ]


# ============================================================
# Case Sessions (Treatment Sessions)
# ============================================================

class CaseSessionSerializer(serializers.ModelSerializer):
    """
    Read-only session serializer:
    - Patient: read-only
    - Student: read-only after creation
    - Supervisor: review
    """

    student = UserSerializer(read_only=True)
    supervisor = UserSerializer(read_only=True)

    class Meta:
        model = CaseSession
        fields = [
            "id",
            "case",
            "student",
            "supervisor",
            "notes",
            "status",
            "supervisor_feedback",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CaseSessionCreateSerializer(serializers.ModelSerializer):
    """
    Create treatment session.
    Allowed ONLY for assigned student.
    """

    class Meta:
        model = CaseSession
        fields = [
            "case",
            "notes",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)
        case = attrs.get("case")

        if not user or user.role != "student":
            raise serializers.ValidationError(
                _("Only students can create treatment sessions.")
            )

        if case.student_id != user.id:
            raise serializers.ValidationError(
                _("You are not assigned to this case.")
            )

        if case.status not in {
            Case.Status.ASSIGNED,
            Case.Status.IN_PROGRESS,
        }:
            raise serializers.ValidationError(
                _("Sessions can only be created for active cases.")
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        user = resolve_request_user(request)
        case = validated_data["case"]

        session = CaseSession.objects.create(
            case=case,
            student=user,
            supervisor=case.supervisor,
            status=CaseSession.Status.COMPLETED,
            notes=validated_data["notes"],
        )

        CaseHistory.objects.create(
            case=case,
            action=CaseHistory.Action.SESSION_CREATED,
            description=_("Treatment session created by student."),
            performed_by=user,
        )

        if case.status == Case.Status.ASSIGNED:
            case.status = Case.Status.IN_PROGRESS
            case.save(update_fields=["status"])

        return session


class CaseSessionReviewSerializer(serializers.ModelSerializer):
    """
    Supervisor review of a completed session.
    """

    class Meta:
        model = CaseSession
        fields = [
            "status",
            "supervisor_feedback",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)
        session = self.instance

        if not user or user.role != "supervisor":
            raise serializers.ValidationError(
                _("Only supervisors can review sessions.")
            )

        if session.supervisor_id != user.id:
            raise serializers.ValidationError(
                _("You are not assigned to review this session.")
            )

        if session.status not in {
            CaseSession.Status.COMPLETED,
            CaseSession.Status.NEEDS_REVIEW,
        }:
            raise serializers.ValidationError(
                _("This session cannot be reviewed.")
            )

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = resolve_request_user(request)

        instance = super().update(instance, validated_data)

        CaseHistory.objects.create(
            case=instance.case,
            action=CaseHistory.Action.SESSION_REVIEWED,
            description=_("Session reviewed by supervisor."),
            performed_by=user,
        )

        return instance


# ============================================================
# Case (READ – Full View)
# ============================================================

class CaseSerializer(serializers.ModelSerializer):
    patient = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    supervisor = UserSerializer(read_only=True)

    history = CaseHistorySerializer(many=True, read_only=True)
    assignment_requests = CaseAssignmentRequestSerializer(many=True, read_only=True)
    sessions = CaseSessionSerializer(many=True, read_only=True)

    class Meta:
        model = Case
        fields = [
            "id",
            "title",
            "description",
            "patient",
            "student",
            "supervisor",
            "status",
            "priority",
            "is_public",
            "created_at",
            "updated_at",
            "history",
            "assignment_requests",
            "sessions",
        ]
        read_only_fields = fields


# ============================================================
# Case Create
# ============================================================

class CaseCreateSerializer(serializers.ModelSerializer):
    """
    Create a new dental case.

    - Patient: can create ONLY for himself
    - Admin/Staff: can create for patient_id
    """

    patient_id = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Case
        fields = [
            "title",
            "description",
            "priority",
            "is_public",
            "patient_id",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)

        if not user:
            raise serializers.ValidationError(_("Authentication required."))

        if user.role == "patient":
            active_exists = Case.objects.filter(
                patient=user,
                status__in=Case.ACTIVE_STATUSES,
            ).exists()

            if active_exists:
                raise serializers.ValidationError(
                    _("You already have an active case.")
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        user = resolve_request_user(request)

        patient_id = validated_data.pop("patient_id", None)

        if user.role == "patient":
            patient = user
        else:
            patient = User.objects.filter(
                id=patient_id,
                role="patient",
            ).first()

        if not patient:
            raise serializers.ValidationError(
                {"patient_id": _("Valid patient is required.")}
            )

        case = Case.objects.create(
            patient=patient,
            **validated_data,
        )

        CaseHistory.objects.create(
            case=case,
            action=CaseHistory.Action.CREATED,
            description=_("Case created."),
            performed_by=user,
        )

        return case


# ============================================================
# Case Update
# ============================================================

class CaseUpdateSerializer(serializers.ModelSerializer):
    """
    Update case metadata.
    - NOT allowed for patients
    - NOT allowed if case is closed
    """

    class Meta:
        model = Case
        fields = [
            "title",
            "description",
            "status",
            "priority",
            "is_public",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)
        case = self.instance

        if case.status == Case.Status.CLOSED:
            raise serializers.ValidationError(
                _("Closed cases cannot be modified.")
            )

        if user and user.role == "patient":
            raise serializers.ValidationError(
                _("Patients cannot modify case details.")
            )

        return attrs
