# apps/cases/services.py
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from apps.audit.services import log_audit_event
from apps.accounts.models import Role
from .models import Case


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
