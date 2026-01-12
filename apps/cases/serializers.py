# apps/cases/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from apps.accounts.models import User, Role
from apps.universities.models import University
from medismile.utils.auth import resolve_request_user

from .models import Case, CaseHistory, CaseAssignmentRequest, CaseSession, AIAnalysisSession, AIProposedCase
from .services import assign_case
from apps.notifications.models import Notification
from django.contrib.contenttypes.models import ContentType


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


class StudentAssignmentRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True, allow_null=True)


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
class CaseCreateSerializer(serializers.Serializer):
    university_id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    priority = serializers.ChoiceField(choices=Case.Priority.choices, required=False)

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)

        if not user or getattr(getattr(user, "role", None), "name", None) != Role.PATIENT:
            raise serializers.ValidationError(_("Only patients can create cases."))

        university = University.objects.filter(id=attrs["university_id"], is_active=True).first()
        if not university:
            raise serializers.ValidationError({"university_id": _("University not found or inactive.")})

        attrs["university"] = university
        return attrs


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

        # If making case public or moving into assignment flow => require university
        new_status = attrs.get("status")
        new_public = attrs.get("is_public", case.is_public)
        new_university = attrs.get("university", case.university)

        if new_public or new_status in {Case.Status.ACCEPTED, Case.Status.NEEDS_ASSIGNMENT_APPROVAL}:
            if not new_university:
                raise serializers.ValidationError(_("University is required for public/assignment cases."))

        return attrs


# ============================================================
# Case Status Update (Dedicated path for state transitions)
# ============================================================
class CaseStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Update case status (and optionally attach university before routing).

    - Allows moving NEW -> ACCEPTED/REJECTED (supervisor decision)
    - Supervisors can move their assigned cases along allowed transitions
    - Tech Support / University Admin (same university) can manage unassigned cases
    """

    class Meta:
        model = Case
        fields = ("status", "university")
        extra_kwargs = {
            "university": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        case: Case = self.instance
        target_status = attrs.get("status", case.status)
        target_university = attrs.get("university", case.university)

        if case.status == Case.Status.CLOSED:
            raise serializers.ValidationError(_("Closed cases cannot be modified."))

        if target_status != case.status:
            allowed = Case.ALLOWED_TRANSITIONS.get(case.status, set())
            if target_status not in allowed:
                raise serializers.ValidationError(
                    {"status": _("Invalid status transition from %(from)s to %(to)s.") % {"from": case.status, "to": target_status}}
                )

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = resolve_request_user(request)

        previous_status = instance.status
        instance.status = validated_data.get("status", instance.status)

        if "university" in validated_data:
            instance.university = validated_data.get("university")

        if "status" in validated_data:
            if instance.status == Case.Status.ACCEPTED and not instance.student_id:
                instance.is_public = True
            else:
                instance.is_public = False

        instance.save()

        CaseHistory.objects.create(
            case=instance,
            action=CaseHistory.Action.STATUS_CHANGED,
            description=_("Status changed from %(from)s to %(to)s.") % {"from": previous_status, "to": instance.status},
            performed_by=user,
        )

        return instance


# ============================================================
# Assignment Request Decision (Supervisor)
# ============================================================
class CaseAssignmentRequestDecisionSerializer(serializers.ModelSerializer):
    decision = serializers.ChoiceField(choices=["accept", "reject"])
    supervisor_response = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = CaseAssignmentRequest
        fields = ("decision", "supervisor_response")

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)
        if not user or getattr(getattr(user, "role", None), "name", None) != Role.SUPERVISOR:
            raise serializers.ValidationError(_("Only supervisors can decide on assignment requests."))

        assignment: CaseAssignmentRequest = self.instance
        if assignment.status != CaseAssignmentRequest.Status.PENDING:
            raise serializers.ValidationError(_("This assignment request is already processed."))

        if assignment.case.supervisor_id and assignment.case.supervisor_id != user.id:
            raise serializers.ValidationError(_("You are not the supervisor of this case."))

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = resolve_request_user(request)
        decision = validated_data["decision"]
        response = validated_data.get("supervisor_response")

        if decision == "accept":
            instance.status = CaseAssignmentRequest.Status.ACCEPTED
            assign_case(supervisor=user, case=instance.case, student=instance.student)
            instance.case.save(update_fields=["status", "student", "supervisor", "is_public"])

            CaseHistory.objects.create(
                case=instance.case,
                action=CaseHistory.Action.ASSIGNED,
                description=_("Case assigned to student via supervisor decision."),
                performed_by=user,
            )

            self._notify_assignment(instance, user, accepted=True)

        else:
            instance.status = CaseAssignmentRequest.Status.REJECTED
            self._notify_assignment(instance, user, accepted=False)

        instance.supervisor_response = response
        instance.save(update_fields=["status", "supervisor_response", "updated_at"])
        return instance

    def _notify_assignment(self, assignment: CaseAssignmentRequest, supervisor, accepted: bool):
        from apps.notifications.models import Notification
        ct = ContentType.objects.get_for_model(assignment.case)
        notif_type = "case_assigned" if accepted else "case_status_changed"
        title = "Case assigned" if accepted else "Case assignment rejected"
        msg = (
            f"Your request for case '{assignment.case.title}' was accepted."
            if accepted
            else f"Your request for case '{assignment.case.title}' was rejected."
        )
        recipients = [assignment.student]
        if assignment.case.patient_id:
            from apps.accounts.models import User
            try:
                recipients.append(assignment.case.patient)
            except Exception:
                pass

        Notification.objects.bulk_create([
            Notification(
                sender=supervisor,
                recipient=recipient,
                notification_type=notif_type,
                priority=Notification.Priority.HIGH if accepted else Notification.Priority.NORMAL,
                title=title,
                message=msg,
                target_content_type=ct,
                target_object_id=assignment.case.id,
                payload={"assignment_request_id": str(assignment.id), "accepted": accepted},
            )
            for recipient in recipients
        ])


# ============================================================
# Assign Supervisor (scopes case to supervisor's university)
# ============================================================
class CaseAssignSupervisorSerializer(serializers.ModelSerializer):
    supervisor_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Case
        fields = ("supervisor_id",)

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)
        case: Case = self.instance

        if case.status == Case.Status.CLOSED:
            raise serializers.ValidationError(_("Closed cases cannot be modified."))

        # pick supervisor: requester if supervisor, else provided
        supervisor = user if getattr(user, "role", None) and user.role.name == Role.SUPERVISOR else None
        supervisor_id = attrs.get("supervisor_id")

        if not supervisor:
            if not supervisor_id:
                raise serializers.ValidationError({"supervisor_id": _("Supervisor is required.")})
            supervisor = User.objects.filter(id=supervisor_id, role__name=Role.SUPERVISOR).first()

        if not supervisor:
            raise serializers.ValidationError({"supervisor_id": _("Valid supervisor not found.")})

        # ensure supervisor has university
        supervisor_university_id = getattr(getattr(supervisor, "supervisorprofile_profile", None), "university_id", None)
        if not supervisor_university_id:
            raise serializers.ValidationError(_("Supervisor must be linked to a university."))

        # cannot override another supervisor
        if case.supervisor_id and case.supervisor_id != supervisor.id:
            raise serializers.ValidationError(_("Case already assigned to another supervisor."))

        attrs["resolved_supervisor"] = supervisor
        attrs["resolved_supervisor_university_id"] = supervisor_university_id
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = resolve_request_user(request)

        supervisor = validated_data["resolved_supervisor"]
        supervisor_university_id = validated_data["resolved_supervisor_university_id"]

        instance.supervisor = supervisor
        instance.university_id = supervisor_university_id
        instance.student = None  # reset student (open for assignment)
        instance.is_public = True  # open only to students of this university (enforced by selectors/validators)
        instance.status = Case.Status.ACCEPTED
        instance.save()

        CaseHistory.objects.create(
            case=instance,
            action=CaseHistory.Action.STATUS_CHANGED,
            description=_("Supervisor %(sup)s scoped case to university %(univ)s.") % {
                "sup": supervisor.email,
                "univ": supervisor_university_id,
            },
            performed_by=user,
        )

        return instance


# ============================================================
# AI Proposals (Fusion Output)
# ============================================================

class AIProposalSourceSerializer(serializers.Serializer):
    vision = serializers.JSONField(required=False)
    text = serializers.JSONField(required=False)


class AIProposalFusionDecisionSerializer(serializers.Serializer):
    decision_label = serializers.CharField()
    final_diagnosis = serializers.CharField()
    final_category = serializers.CharField()
    confidence_level = serializers.CharField()
    match_score = serializers.FloatField()
    urgency_level = serializers.CharField()
    requires_supervisor_review = serializers.BooleanField()
    safety_flags = serializers.ListField(child=serializers.CharField(), required=False)
    explanations = serializers.ListField(child=serializers.JSONField(), required=False)


class AIProposalMedicalReportSerializer(serializers.Serializer):
    summary = serializers.CharField()
    image_findings = serializers.CharField()
    symptom_analysis = serializers.CharField()
    recommendation = serializers.CharField()
    disclaimer = serializers.CharField()
    report_version = serializers.CharField()
    report_text = serializers.CharField()


class AIProposalSerializer(serializers.Serializer):
    proposal_id = serializers.CharField()
    tooth_id = serializers.IntegerField(required=False, allow_null=True)
    source = AIProposalSourceSerializer()
    fusion_decision = AIProposalFusionDecisionSerializer()
    medical_report = AIProposalMedicalReportSerializer()
    metadata = serializers.JSONField(required=False)


class AIProposalBatchSerializer(serializers.Serializer):
    case_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    request_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    session_summary = serializers.JSONField(required=False)
    proposed_cases = serializers.ListField(child=AIProposalSerializer())
    unassigned_lesions = serializers.JSONField(required=False)
    ui_hints = serializers.JSONField(required=False)
    university = serializers.UUIDField(required=True)

    def validate(self, attrs):
        if not attrs.get("proposed_cases"):
            raise serializers.ValidationError(_("No proposed cases provided."))
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        patient = resolve_request_user(request)
        if not patient or getattr(getattr(patient, "role", None), "name", None) != Role.PATIENT:
            raise serializers.ValidationError(_("Only patients can submit AI proposals."))

        session = AIAnalysisSession.objects.create(
            patient=patient,
            university_id=validated_data["university"],
            case_id_external=validated_data.get("case_id"),
            request_id=validated_data.get("request_id"),
            session_summary=validated_data.get("session_summary"),
            ui_hints=validated_data.get("ui_hints"),
        )

        proposals = []
        for item in validated_data["proposed_cases"]:
            proposals.append(
                AIProposedCase(
                    session=session,
                    proposal_id=item["proposal_id"],
                    tooth_id=item.get("tooth_id"),
                    fusion_decision=item.get("fusion_decision"),
                    medical_report=item.get("medical_report"),
                    metadata=item.get("metadata"),
                    raw_proposal=item,
                )
            )
        AIProposedCase.objects.bulk_create(proposals)
        return session


class AIProposalDecisionSerializer(serializers.Serializer):
    proposal_id = serializers.CharField()
    decision = serializers.ChoiceField(choices=["accept", "reject"])


class AIProposalNextSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    proposal_id = serializers.CharField()
    tooth_id = serializers.IntegerField(required=False, allow_null=True)
    fusion_decision = AIProposalFusionDecisionSerializer()
    medical_report = AIProposalMedicalReportSerializer()
    metadata = serializers.JSONField(required=False)
    raw_proposal = serializers.JSONField()


# Supervisor decision on new cases
class SupervisorCaseDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accept", "reject"])
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Supervisor decision on assignment
class AssignmentDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
