# apps/cases/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from apps.accounts.models import User, Role
from medismile.utils.auth import resolve_request_user

from .models import Case, CaseHistory, CaseAssignmentRequest, CaseSession


# ============================================================
# Lightweight User Serializer (LOCAL to cases)
# Avoid cross-app tight coupling with accounts serializers.
# ============================================================
class CaseUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role")
        read_only_fields = fields


# ============================================================
# Case History (READ ONLY)
# ============================================================
class CaseHistorySerializer(serializers.ModelSerializer):
    performed_by = CaseUserSerializer(read_only=True)

    class Meta:
        model = CaseHistory
        fields = ("id", "action", "description", "performed_by", "created_at")
        read_only_fields = fields


# ============================================================
# Assignment Requests
# ============================================================
class CaseAssignmentRequestSerializer(serializers.ModelSerializer):
    student = CaseUserSerializer(read_only=True)

    class Meta:
        model = CaseAssignmentRequest
        fields = (
            "id",
            "case",
            "student",
            "message",
            "status",
            "supervisor_response",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "student",
            "status",
            "supervisor_response",
            "created_at",
            "updated_at",
        )


# ============================================================
# Sessions
# ============================================================
class CaseSessionSerializer(serializers.ModelSerializer):
    student = CaseUserSerializer(read_only=True)
    supervisor = CaseUserSerializer(read_only=True)

    class Meta:
        model = CaseSession
        fields = (
            "id",
            "case",
            "student",
            "supervisor",
            "notes",
            "status",
            "supervisor_feedback",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CaseSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseSession
        fields = ("case", "notes")

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)
        case = attrs.get("case")

        if not user:
            raise serializers.ValidationError(_("Authentication required."))

        if user.role.name != Role.STUDENT:
            raise serializers.ValidationError(_("Only students can create treatment sessions."))

        if case.student_id != user.id:
            raise serializers.ValidationError(_("You are not assigned to this case."))

        if case.status not in {Case.Status.ASSIGNED, Case.Status.IN_PROGRESS}:
            raise serializers.ValidationError(_("Sessions can only be created for active cases."))

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

        # auto-move case to in_progress on first session
        if case.status == Case.Status.ASSIGNED:
            case.status = Case.Status.IN_PROGRESS
            case.save(update_fields=["status"])

        return session


class CaseSessionReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseSession
        fields = ("status", "supervisor_feedback")

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)
        session: CaseSession = self.instance

        if not user:
            raise serializers.ValidationError(_("Authentication required."))

        if user.role.name != Role.SUPERVISOR:
            raise serializers.ValidationError(_("Only supervisors can review sessions."))

        if session.supervisor_id != user.id:
            raise serializers.ValidationError(_("You are not assigned to review this session."))

        if session.status not in {CaseSession.Status.COMPLETED, CaseSession.Status.NEEDS_REVIEW}:
            raise serializers.ValidationError(_("This session cannot be reviewed."))

        next_status = attrs.get("status")
        if next_status not in {CaseSession.Status.APPROVED, CaseSession.Status.REJECTED}:
            raise serializers.ValidationError(_("Invalid review status."))

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
    university_id = serializers.UUIDField(source="university.id", read_only=True)
    university_name = serializers.CharField(source="university.name", read_only=True)

    patient = CaseUserSerializer(read_only=True)
    student = CaseUserSerializer(read_only=True)
    supervisor = CaseUserSerializer(read_only=True)

    history = CaseHistorySerializer(many=True, read_only=True)
    assignment_requests = CaseAssignmentRequestSerializer(many=True, read_only=True)
    sessions = CaseSessionSerializer(many=True, read_only=True)

    class Meta:
        model = Case
        fields = (
            "id",
            "title",
            "description",
            "university_id",
            "university_name",
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
        )
        read_only_fields = fields


# ============================================================
# Case Create
# ============================================================
class CaseCreateSerializer(serializers.ModelSerializer):
    """
    Create a new dental case.

    - Patient: can create ONLY for himself (university not required initially)
    - Non-patient creation: may set patient_id and (optionally) university
    """

    patient_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    university_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Case
        fields = ("title", "description", "priority", "is_public", "patient_id", "university_id")

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)

        if not user:
            raise serializers.ValidationError(_("Authentication required."))

        # Patient can only create for himself and cannot publish immediately
        if user.role.name == Role.PATIENT:
            if attrs.get("patient_id"):
                raise serializers.ValidationError({"patient_id": _("Patients cannot set patient_id.")})
            if attrs.get("is_public"):
                raise serializers.ValidationError(_("Patient cases cannot be public until routed to a university."))

            active_exists = Case.objects.filter(
                patient=user,
                status__in=Case.ACTIVE_STATUSES,
            ).exists()
            if active_exists:
                raise serializers.ValidationError(_("You already have an active case."))

        # If is_public => must have university (either already or provided)
        if attrs.get("is_public"):
            if not attrs.get("university_id"):
                raise serializers.ValidationError({"university_id": _("University is required for public cases.")})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        user = resolve_request_user(request)

        patient_id = validated_data.pop("patient_id", None)
        university_id = validated_data.pop("university_id", None)

        # Resolve patient
        if user.role.name == Role.PATIENT:
            patient = user
        else:
            patient = User.objects.filter(id=patient_id, role__name=Role.PATIENT).first()

        if not patient:
            raise serializers.ValidationError({"patient_id": _("Valid patient is required.")})

        # Build case
        case = Case(
            patient=patient,
            **validated_data,
        )

        # Link university only if provided / non-patient flow
        if university_id:
            case.university_id = university_id

        # If public: enforce pending_assignment status
        if case.is_public:
            case.status = Case.Status.PENDING_ASSIGNMENT

        case.save()

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
    - Patient cannot update case details
    - Closed cases cannot be modified
    """

    class Meta:
        model = Case
        fields = ("title", "description", "status", "priority", "is_public", "university")

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)
        case: Case = self.instance

        if case.status == Case.Status.CLOSED:
            raise serializers.ValidationError(_("Closed cases cannot be modified."))

        if user and user.role.name == Role.PATIENT:
            raise serializers.ValidationError(_("Patients cannot modify case details."))

        # If moving to pending_assignment or public => require university
        new_status = attrs.get("status")
        new_public = attrs.get("is_public", case.is_public)
        new_university = attrs.get("university", case.university)

        if new_public or new_status == Case.Status.PENDING_ASSIGNMENT:
            if not new_university:
                raise serializers.ValidationError(_("University is required for public/assignment cases."))

        return attrs
