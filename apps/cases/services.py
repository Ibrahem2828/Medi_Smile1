# apps/cases/services.py
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.contenttypes.models import ContentType

from apps.audit.services import log_audit_event
from apps.accounts.models import Role, User
from apps.notifications.models import Notification
from .models import Case, CaseHistory, AIProposedCase


def _notify_users_about_case(*, recipients, notification_type, title, message, case, priority=Notification.Priority.NORMAL, sender=None, payload=None):
    if not recipients:
        return
    ct = ContentType.objects.get_for_model(case)
    Notification.objects.bulk_create([
        Notification(
            sender=sender,
            recipient=user,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            target_content_type=ct,
            target_object_id=case.id,
            payload=payload or {},
        )
        for user in recipients
    ])

def _ensure_patient_can_create_case(patient: User):
    if Case.objects.filter(patient=patient, status__in=Case.ACTIVE_STATUSES).exists():
        raise ValidationError(
            {"case": "You already have an active case. Complete it before creating a new one."}
        )


def create_case(*, patient, data: dict) -> Case:
    _ensure_patient_can_create_case(patient)
    case = Case.objects.create(
        patient=patient,
        university=data["university"],
        description=data.get("description", ""),
        priority=data.get("priority"),
    )

    log_audit_event(
        user=patient,
        university=case.university,
        action="cases.case.created",
        description="Patient created a new case",
        content_object=case,
        metadata={"priority": case.priority},
    )

    return case


def assign_case(*, supervisor, case: Case, student):
    if supervisor.role.name != Role.SUPERVISOR:
        raise PermissionDenied

    # lock visibility once assigned to a student
    case.is_public = False
    case.student = student
    case.supervisor = supervisor
    if supervisor.supervisorprofile_profile and supervisor.supervisorprofile_profile.university_id:
        case.university_id = supervisor.supervisorprofile_profile.university_id
    case.status = Case.Status.ASSIGNED
    case.assigned_at = timezone.now()
    case.save()

    log_audit_event(
        user=supervisor,
        university=case.university,
        action="cases.case.assigned",
        description="Case assigned to student",
        content_object=case,
        metadata={
            "student_id": str(student.id),
            "supervisor_id": str(supervisor.id),
        },
    )

    return case


def complete_case(*, supervisor, case: Case):
    if supervisor.role.name != Role.SUPERVISOR:
        raise PermissionDenied

    case.status = Case.Status.COMPLETED
    case.completed_at = timezone.now()
    case.save()

    log_audit_event(
        user=supervisor,
        university=case.university,
        action="cases.case.completed",
        description="Case marked as completed",
        content_object=case,
    )

    return case


# ============================================================
# AI Proposed Case -> Case conversion
# ============================================================

def _priority_from_urgency(urgency: str):
    urgency = (urgency or "").lower()
    if urgency == "high":
        return Case.Priority.HIGH
    if urgency == "medium":
        return Case.Priority.MEDIUM
    if urgency == "low":
        return Case.Priority.LOW
    return Case.Priority.MEDIUM


def create_case_from_proposal(*, patient: User, university_id, proposal: AIProposedCase) -> Case:
    _ensure_patient_can_create_case(patient)
    fusion = proposal.fusion_decision or {}
    medical_report = proposal.medical_report or {}
    urgency = fusion.get("urgency_level")

    # title/description from fusion + report
    title = fusion.get("final_diagnosis") or medical_report.get("summary") or "AI Proposed Case"
    description = medical_report.get("report_text") or medical_report.get("summary") or ""

    case = Case.objects.create(
        patient=patient,
        university_id=university_id,
        title=title,
        description=description,
        priority=_priority_from_urgency(urgency),
        status=Case.Status.NEW,
        is_public=True,
        is_ai_critical=True,
        ai_metadata={
            "fusion_decision": fusion,
            "medical_report": medical_report,
            "metadata": proposal.metadata,
            "raw_proposal": proposal.raw_proposal,
        },
    )

    CaseHistory.objects.create(
        case=case,
        action=CaseHistory.Action.CREATED,
        description="Case created after patient accepted AI proposal.",
        performed_by=patient,
    )

    log_audit_event(
        user=patient,
        university=case.university,
        action="cases.case.created_from_ai_proposal",
        description="Case created from AI proposal after patient approval",
        content_object=case,
        metadata={"proposal_id": proposal.proposal_id},
    )
    return case
