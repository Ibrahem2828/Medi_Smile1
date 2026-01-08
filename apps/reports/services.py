# apps/reports/services.py
import csv
import json
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.models import Role, User, StudentProfile
from apps.audit.services import log_audit_event
from apps.notifications.audit_bridge import notify_on_audit_event
from apps.cases.models import Case
from apps.universities.models import University, Course

from .models import Report
from .selectors import _resolve_university_id


def _get_target_context(target_type: str, target_id):
    if target_type == Report.TargetType.CASE:
        case = Case.objects.filter(id=target_id).select_related("student", "supervisor", "university").first()
        if not case:
            raise ValidationError({"target_id": "Case not found."})
        return {
            "university": case.university,
            "student": case.student,
            "supervisor": case.supervisor,
            "case_id": case.id,
            "target": case,
        }

    if target_type == Report.TargetType.STUDENT:
        student = User.objects.filter(id=target_id, role__name=Role.STUDENT).first()
        if not student:
            raise ValidationError({"target_id": "Student not found."})
        profile = StudentProfile.objects.select_related("university").filter(user=student).first()
        university = profile.university if profile else None
        if not university:
            raise ValidationError({"target_id": "Student is not linked to a university."})
        return {
            "university": university,
            "student": student,
            "supervisor": None,
            "case_id": None,
            "target": student,
        }

    if target_type == Report.TargetType.COURSE:
        course = Course.objects.filter(id=target_id).select_related("university").first()
        if not course:
            raise ValidationError({"target_id": "Course not found."})
        return {
            "university": course.university,
            "student": None,
            "supervisor": None,
            "case_id": None,
            "target": course,
        }

    if target_type == Report.TargetType.UNIVERSITY:
        university = University.objects.filter(id=target_id).first()
        if not university:
            raise ValidationError({"target_id": "University not found."})
        return {
            "university": university,
            "student": None,
            "supervisor": None,
            "case_id": None,
            "target": university,
        }

    raise ValidationError({"target_type": "Invalid target type."})


def create_report(*, actor, data: dict) -> Report:
    role_name = getattr(getattr(actor, "role", None), "name", None)
    if role_name not in {Role.STUDENT, Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        raise PermissionDenied("You are not allowed to create reports.")

    report_type = data["report_type"]
    target_type = data["target_type"]
    target_id = data["target_id"]

    context = _get_target_context(target_type, target_id)
    university = context["university"]

    if not university:
        raise ValidationError({"target_id": "Target is not linked to a university."})

    if role_name == Role.STUDENT:
        if report_type != Report.ReportType.CLINICAL_CASE:
            raise PermissionDenied("Students can only create clinical case reports.")
        if target_type != Report.TargetType.CASE:
            raise PermissionDenied("Students can only report on cases.")
        if not context["student"] or context["student"].id != actor.id:
            raise PermissionDenied("You can only report on your own assigned cases.")

    if role_name == Role.SUPERVISOR:
        supervisor_university_id = _resolve_university_id(actor)
        if not supervisor_university_id:
            raise PermissionDenied("Supervisor profile is not linked to a university.")
        if supervisor_university_id and university.id != supervisor_university_id:
            raise PermissionDenied("You can only create reports within your university.")
        allowed_supervisor_types = {
            Report.ReportType.CLINICAL_CASE,
            Report.ReportType.SUPERVISOR_CASE_EVALUATION,
            Report.ReportType.STUDENT_PERFORMANCE,
            Report.ReportType.COURSE_PERFORMANCE,
        }
        if report_type not in allowed_supervisor_types:
            raise PermissionDenied("Supervisors can only create case/student/course reports.")
        if target_type not in {Report.TargetType.CASE, Report.TargetType.STUDENT, Report.TargetType.COURSE}:
            raise PermissionDenied("Supervisors can only report on cases, students, or courses.")

    if role_name == Role.UNIVERSITY_ADMIN:
        admin_university_id = _resolve_university_id(actor)
        if not admin_university_id:
            raise PermissionDenied("University Admin profile is not linked to a university.")
        allowed_admin_types = {
            Report.ReportType.UNIVERSITY_STUDENTS,
            Report.ReportType.UNIVERSITY_SUPERVISORS,
            Report.ReportType.UNIVERSITY_ARCHIVE,
        }
        if report_type not in allowed_admin_types:
            raise PermissionDenied("University Admin can only create administrative reports.")
        if target_type != Report.TargetType.UNIVERSITY or university.id != admin_university_id:
            raise PermissionDenied("University Admin can only report on their own university.")

    report = Report(
        author=actor,
        author_role=role_name,
        student=context.get("student"),
        supervisor=context.get("supervisor") or (actor if role_name == Role.SUPERVISOR else None),
        university=university,
        generated_by=actor if role_name in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN} else None,
        report_type=report_type,
        target_type=target_type,
        target_id=target_id,
        case_id=context.get("case_id") or data.get("case_id"),
        session_id=data.get("session_id"),
        title=data.get("title"),
        description=data.get("description"),
        content=data.get("content"),
        attachments=data.get("attachments"),
        snapshot_data=data.get("snapshot_data"),
        status=Report.Status.DRAFT,
    )
    try:
        report.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(
            getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
        ) from exc
    report.save()

    log_audit_event(
        user=actor,
        university=university,
        action="reports.report.created",
        description="Report created",
        content_object=report,
        metadata={"report_type": report.report_type, "target_type": report.target_type},
    )

    return report


def update_report(*, actor, report: Report, data: dict) -> Report:
    if report.author_id != actor.id:
        raise PermissionDenied("You can only update your own reports.")

    if report.status not in {Report.Status.DRAFT, Report.Status.REJECTED}:
        raise PermissionDenied("Only draft/rejected reports can be updated.")

    for field, value in data.items():
        setattr(report, field, value)

    if report.status == Report.Status.REJECTED:
        report.status = Report.Status.DRAFT
        report.rejected_at = None

    try:
        report.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(
            getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
        ) from exc
    report.save()

    log_audit_event(
        user=actor,
        university=report.university,
        action="reports.report.updated",
        description="Report updated",
        content_object=report,
    )

    return report


def submit_report(*, actor, report: Report) -> Report:
    if report.author_id != actor.id:
        raise PermissionDenied("You can only submit your own reports.")

    if report.status not in {Report.Status.DRAFT, Report.Status.REJECTED}:
        raise PermissionDenied("Only draft/rejected reports can be submitted.")

    if not report.content:
        raise ValidationError({"content": "Report content is required before submission."})

    report.status = Report.Status.SUBMITTED
    report.submitted_at = timezone.now()
    report.save(update_fields=["status", "submitted_at", "updated_at"])

    log_audit_event(
        user=actor,
        university=report.university,
        action="reports.report.submitted",
        description="Report submitted",
        content_object=report,
    )

    # Notify supervisor (if exists)
    notify_on_audit_event(
        action="reports.report.submitted",
        context={
            "supervisor": report.supervisor,
            "report_id": report.id,
            "report_object": report,
        },
    )

    return report


def approve_report(*, supervisor, report: Report, review_notes: str | None = None, score: int | None = None) -> Report:
    if supervisor.role.name != Role.SUPERVISOR:
        raise PermissionDenied("Only supervisors can approve reports.")

    if report.status != Report.Status.SUBMITTED:
        raise PermissionDenied("Only submitted reports can be approved.")

    supervisor_university_id = _resolve_university_id(supervisor)
    if supervisor_university_id and report.university_id != supervisor_university_id:
        raise PermissionDenied("You cannot approve reports outside your university.")

    report.status = Report.Status.LOCKED
    report.review_notes = review_notes or report.review_notes
    report.score = score if score is not None else report.score
    report.approved_by = supervisor
    report.approved_at = timezone.now()
    report.reviewed_at = report.approved_at
    report.locked_at = report.approved_at
    report.save(update_fields=[
        "status",
        "review_notes",
        "score",
        "approved_by",
        "approved_at",
        "reviewed_at",
        "locked_at",
        "updated_at",
    ])

    log_audit_event(
        user=supervisor,
        university=report.university,
        action="reports.report.approved",
        description="Report approved",
        content_object=report,
    )

    notify_on_audit_event(
        action="reports.report.approved",
        context={
            "author": report.author,
            "report_id": report.id,
            "report_object": report,
        },
    )

    return report


def reject_report(*, supervisor, report: Report, review_notes: str) -> Report:
    if supervisor.role.name != Role.SUPERVISOR:
        raise PermissionDenied("Only supervisors can reject reports.")

    if report.status != Report.Status.SUBMITTED:
        raise PermissionDenied("Only submitted reports can be rejected.")

    supervisor_university_id = _resolve_university_id(supervisor)
    if supervisor_university_id and report.university_id != supervisor_university_id:
        raise PermissionDenied("You cannot reject reports outside your university.")

    report.status = Report.Status.REJECTED
    report.review_notes = review_notes
    report.rejected_at = timezone.now()
    report.reviewed_at = report.rejected_at
    report.save(update_fields=["status", "review_notes", "rejected_at", "reviewed_at", "updated_at"])

    log_audit_event(
        user=supervisor,
        university=report.university,
        action="reports.report.rejected",
        description="Report rejected",
        content_object=report,
        metadata={"reason": review_notes},
    )

    notify_on_audit_event(
        action="reports.report.rejected",
        context={
            "author": report.author,
            "report_id": report.id,
            "report_object": report,
            "reason": review_notes,
        },
    )

    return report


def _render_report_text(report: Report) -> str:
    payload = {
        "id": str(report.id),
        "report_type": report.report_type,
        "target_type": report.target_type,
        "target_id": str(report.target_id),
        "status": report.status,
        "title": report.title,
        "description": report.description,
        "content": report.content,
        "review_notes": report.review_notes,
        "approved_at": report.approved_at.isoformat() if report.approved_at else None,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _generate_pdf_bytes(report: Report) -> bytes:
    # Minimal PDF generation without external dependencies.
    text = _render_report_text(report).replace("(", "\\(").replace(")", "\\)")
    lines = text.splitlines() or ["Report"]

    content_lines = ["BT", "/F1 12 Tf", "72 720 Td"]
    for idx, line in enumerate(lines):
        if idx > 0:
            content_lines.append("0 -14 Td")
        content_lines.append(f"({line}) Tj")
    content_lines.append("ET")
    content_stream = "\n".join(content_lines).encode("utf-8")

    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    objects.append(
        b"4 0 obj\n<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\nstream\n" + content_stream + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    xref_positions = []
    pdf = b"%PDF-1.4\n"
    for obj in objects:
        xref_positions.append(len(pdf))
        pdf += obj

    xref_start = len(pdf)
    pdf += b"xref\n0 %d\n" % (len(objects) + 1)
    pdf += b"0000000000 65535 f \n"
    for pos in xref_positions:
        pdf += f"{pos:010d} 00000 n \n".encode("ascii")

    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    pdf += b"startxref\n" + str(xref_start).encode("ascii") + b"\n%%EOF"
    return pdf


def export_report(*, actor, report: Report, fmt: str) -> str:
    if actor.role.name != Role.UNIVERSITY_ADMIN:
        raise PermissionDenied("Only University Admin can export reports.")

    admin_university_id = _resolve_university_id(actor)
    if admin_university_id and report.university_id != admin_university_id:
        raise PermissionDenied("You cannot export reports outside your university.")

    exports_dir = Path(settings.MEDIA_ROOT) / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "report_type", "target_type", "target_id", "status", "title", "created_at"])
        writer.writerow([report.id, report.report_type, report.target_type, report.target_id, report.status, report.title, report.created_at])
        filename = exports_dir / f"report_{report.id}.csv"
        filename.write_text(buffer.getvalue(), encoding="utf-8")
    else:
        pdf_bytes = _generate_pdf_bytes(report)
        filename = exports_dir / f"report_{report.id}.pdf"
        filename.write_bytes(pdf_bytes)

    report.file_url = f"/media/exports/{filename.name}"
    report.save(update_fields=["file_url", "updated_at"])

    log_audit_event(
        user=actor,
        university=report.university,
        action="reports.report.exported",
        description="Report exported",
        content_object=report,
        metadata={"format": fmt},
    )

    return report.file_url
