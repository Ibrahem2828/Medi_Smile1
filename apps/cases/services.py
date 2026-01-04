# apps/cases/services.py
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType

from apps.audit.services import log_audit_event
from apps.accounts.models import Role, User
from apps.notifications.models import Notification
from .models import Case


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


def create_case(*, patient, data: dict) -> Case:
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


def create_case_from_ai(*, patient: User, university, ai_payload: dict, title: str | None = None, description: str | None = None) -> Case:
    """
    Create a critical case from AI diagnosis payload.
    """
    priority = Case.Priority.URGENT if ai_payload.get("severity_level") == "high" or ai_payload.get("urgency") == "urgent" else Case.Priority.HIGH
    case = Case.objects.create(
        patient=patient,
        university=university,
        title=title or ai_payload.get("diagnosis") or "AI Critical Case",
        description=description or ai_payload.get("patient_explanation") or "",
        priority=priority,
        status=Case.Status.PENDING_ASSIGNMENT,
        is_public=True,
        is_ai_critical=True,
        ai_metadata=ai_payload,
    )

    log_audit_event(
        user=patient,
        university=case.university,
        action="cases.case.created_from_ai",
        description="Case created from AI critical diagnosis",
        content_object=case,
        metadata={"priority": case.priority, "ai": ai_payload},
    )

    # Notify supervisors in the selected university
    supervisors = User.objects.filter(
        role__name=Role.SUPERVISOR,
        supervisorprofile_profile__university=university,
    )
    _notify_users_about_case(
        recipients=supervisors,
        notification_type="case_created",
        title=_("حالة حرجة جديدة بانتظار مشرف"),
        message=_("حالة حرجة تم إنشاؤها من تشخيص الذكاء للمريض %(email)s تحتاج مراجعة.") % {"email": patient.email},
        case=case,
        priority=Notification.Priority.CRITICAL,
        sender=patient,
        payload={"ai": ai_payload},
    )

    return case
