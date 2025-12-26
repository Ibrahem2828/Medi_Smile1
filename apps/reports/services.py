# apps/reports/services.py
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.services import log_audit_event
from apps.notifications.audit_bridge import notify_on_audit_event

from .models import Report


# ============================================================
# Report Services
# ============================================================

def generate_report(*, actor, data: dict) -> Report:
    """
    Generate a new report.

    Allowed:
    - Supervisor
    - University Admin
    - Tech Support
    """
    role_name = actor.role.name

    if role_name not in {
        Role.SUPERVISOR,
        Role.UNIVERSITY_ADMIN,
        Role.TECH_SUPPORT,
    }:
        raise PermissionDenied("You are not allowed to generate reports.")

    report = Report.objects.create(
        student=data["student"],
        university=data["university"],
        report_type=data["report_type"],
        title=data.get("title"),
        description=data.get("description"),
        file_url=data["file_url"],
        snapshot_data=data.get("snapshot_data"),
        generated_by=actor,
    )

    log_audit_event(
        user=actor,
        university=report.university,
        action="reports.report.generated",
        description="Report generated",
        content_object=report,
        metadata={"report_type": report.report_type},
    )

    return report


def toggle_report_visibility(*, actor, report: Report, is_active: bool) -> Report:
    """
    Soft toggle report visibility.
    """
    role_name = actor.role.name

    if role_name == Role.TECH_SUPPORT:
        report.is_active = is_active
        report.save(update_fields=["is_active", "updated_at"])

    elif role_name == Role.UNIVERSITY_ADMIN:
        if report.university_id != actor.university_id:
            raise PermissionDenied("You cannot modify reports outside your university.")
        report.is_active = is_active
        report.save(update_fields=["is_active", "updated_at"])

    else:
        raise PermissionDenied("You are not allowed to modify report visibility.")

    log_audit_event(
        user=actor,
        university=report.university,
        action="reports.report.visibility_changed",
        description="Report visibility toggled",
        content_object=report,
        metadata={"is_active": is_active},
    )

    return report


# ============================================================
# Academic Flow Reports
# ============================================================

def submit_report(*, student, case, data: dict) -> Report:
    if student.role.name != Role.STUDENT:
        raise PermissionDenied("Only students can submit reports.")

    report = Report.objects.create(
        student=student,
        case=case,
        content=data["content"],
        submitted_at=timezone.now(),
    )

    log_audit_event(
        user=student,
        university=case.university,
        action="reports.report.submitted",
        description="Student submitted case report",
        content_object=report,
        metadata={"case_id": str(case.id)},
    )

    # Notify supervisor (if exists)
    notify_on_audit_event(
        action="reports.report.submitted",
        context={
            "supervisor": case.supervisor,
            "report_id": report.id,
            "report_object": report,
            "case_id": case.id,
        },
    )

    return report


def review_report(*, supervisor, report: Report, feedback: str) -> Report:
    if supervisor.role.name != Role.SUPERVISOR:
        raise PermissionDenied("Only supervisors can review reports.")

    report.reviewed_by = supervisor
    report.feedback = feedback
    report.reviewed_at = timezone.now()
    report.save()

    log_audit_event(
        user=supervisor,
        university=report.case.university,
        action="reports.report.reviewed",
        description="Supervisor reviewed report",
        content_object=report,
        metadata={"student_id": str(report.student_id)},
    )

    return report
