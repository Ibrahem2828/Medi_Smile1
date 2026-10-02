# apps/cases/services.py
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from apps.audit.services import log_audit_event
from apps.accounts.models import Role, User
from medismile.utils.scoping import get_user_university_id
from apps.notifications.models import Notification
from .models import Case, CaseHistory, CaseAssignmentRequest, AIProposedCase


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
    payload = {
        "patient": patient,
        "university": data["university"],
        "title": data["title"],
        "description": data["description"],
    }
    priority = data.get("priority")
    if priority:
        payload["priority"] = priority
    case = Case.objects.create(**payload)

    log_audit_event(
        user=patient,
        university=case.university,
        action="cases.case.created",
        description="Patient created a new case",
        content_object=case,
        metadata={"priority": case.priority},
    )

    return case


def create_ai_critical_case(
    *,
    patient,
    university,
    diagnosis_id,
    title: str = "",
    description: str = "",
) -> tuple[Case, bool]:
    """
    Turn a patient's AI analysis into a routable case for ``university``.

    ``POST /api/ai/diagnose/`` already auto-creates a lightweight, unscoped
    case. When that case is still NEW and unscoped it is *promoted* (scoped to
    the chosen university, flagged AI-critical, report attached) instead of
    creating a duplicate. Otherwise a fresh case is created.

    Returns ``(case, created)``.
    """
    from apps.ai.models import AIDiagnosis  # local import: ai depends on cases

    with transaction.atomic():
        diagnosis = (
            AIDiagnosis.objects.select_related("case")
            .select_for_update()
            .filter(id=diagnosis_id, patient=patient)
            .first()
        )
        if diagnosis is None:
            raise ValidationError({"diagnosis_id": "Diagnosis not found."})
        if diagnosis.status not in {"completed", "reviewed"}:
            raise ValidationError({"diagnosis_id": "Diagnosis is not a completed server analysis."})
        primary = str(diagnosis.primary_diagnosis or diagnosis.diagnosis_label or "").strip()
        if not primary:
            raise ValidationError({"diagnosis_id": "Diagnosis has insufficient evidence for case routing."})

        candidate = getattr(diagnosis, "case", None)
        promotable = (
            candidate is not None
            and candidate.patient_id == patient.id
            and candidate.status == Case.Status.NEW
            and candidate.university_id is None
        )
        trusted_metadata = {
            "source": "server_ai_diagnosis",
            "diagnosis_id": str(diagnosis.id),
            "primary_diagnosis": primary,
            "confidence_level": diagnosis.confidence_level,
            "severity_level": diagnosis.severity_level,
            "urgency_level": diagnosis.urgency_level,
            "model_versions": (diagnosis.ai_metadata or {}).get("model_versions"),
        }
        report_title = title or f"AI: {primary}"
        if promotable:
            case = candidate
            case.university = university
            case.is_ai_critical = True
            case.ai_metadata = trusted_metadata
            if title:
                case.title = title[:200]
            if description:
                case.description = description
            case.save()
            created = False
        else:
            # Same one-active-case rule as a manual case.
            _ensure_patient_can_create_case(patient)
            case = Case.objects.create(
                patient=patient,
                university=university,
                title=report_title[:200],
                description=description or diagnosis.patient_explanation or "AI analysis",
                is_ai_critical=True,
                ai_metadata=trusted_metadata,
            )
            created = True

        CaseHistory.objects.create(
            case=case,
            action=CaseHistory.Action.CREATED if created else CaseHistory.Action.STATUS_CHANGED,
            description="AI-critical case submitted to university by patient.",
            performed_by=patient,
        )

    log_audit_event(
        user=patient,
        university=university,
        action="cases.case.ai_critical_submitted",
        description="Patient submitted AI analysis as a case",
        content_object=case,
        metadata={"created": created, "diagnosis_id": str(diagnosis.id) if diagnosis else None},
    )
    return case, created


def assign_case(*, supervisor, case: Case, student):
    if supervisor.role.name != Role.SUPERVISOR:
        raise PermissionDenied

    supervisor_university_id = get_user_university_id(supervisor)
    if not supervisor_university_id:
        raise PermissionDenied
    # Never re-home a case: a supervisor may only take cases that are already
    # in their university (or still unscoped).
    if case.university_id and case.university_id != supervisor_university_id:
        raise PermissionDenied

    # lock visibility once assigned to a student
    case.is_public = False
    case.student = student
    case.supervisor = supervisor
    case.university_id = supervisor_university_id
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


@transaction.atomic
def request_case_assignment(*, student: User, case_id, message: str | None = None) -> CaseAssignmentRequest:
    if getattr(getattr(student, "role", None), "name", None) != Role.STUDENT:
        raise PermissionDenied("Only students can request case assignment.")

    student_university_id = getattr(getattr(student, "studentprofile_profile", None), "university_id", None)
    case = Case.objects.select_for_update().filter(id=case_id, university_id=student_university_id).first()
    if not case or case.status != Case.Status.ACCEPTED or not case.is_public:
        raise ValidationError({"case": "Case not available for assignment."})

    existing = CaseAssignmentRequest.objects.filter(case=case, student=student).first()
    if existing:
        raise ValidationError({"case": "Assignment request already exists."})

    req = CaseAssignmentRequest.objects.create(case=case, student=student, message=message)
    req.apply_to_case()

    CaseHistory.objects.create(
        case=case,
        action=CaseHistory.Action.ASSIGNMENT_REQUESTED,
        description="Student requested assignment.",
        performed_by=student,
    )

    return req


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
