# apps/reports/services.py
import csv
import json
import re
from datetime import date
from io import StringIO, BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.models import Role, User, StudentProfile, SupervisorProfile, PatientProfile
from apps.audit.services import log_audit_event
from apps.notifications.audit_bridge import notify_on_audit_event
from apps.cases.models import Case
from apps.universities.models import University, Course
from medismile.utils.scoping import get_user_university_id

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


def _server_snapshot(context: dict) -> dict:
    """Build the small, immutable part of a report snapshot from DB records.

    Report JSON is authored by a user and is therefore presentation data only.
    It must never become an authority for resolving a patient, case or staff
    record during a later export.  The target and university below are written
    by the server so they can be checked again when the report is exported.
    """
    target = context["target"]
    return {
        "snapshot_version": 1,
        "created_at": timezone.now().isoformat(),
        "target": {
            "id": str(target.id),
            "type": target.__class__.__name__.lower(),
        },
        "university_id": str(context["university"].id),
        "case_id": str(context["case_id"]) if context.get("case_id") else None,
        "student_id": str(context["student"].id) if context.get("student") else None,
        "supervisor_id": str(context["supervisor"].id) if context.get("supervisor") else None,
    }


def _scoped_user(user_id, *, university_id, role_name: str | None = None):
    """Resolve a user only when their profile belongs to the report university."""
    if not user_id:
        return None
    query = User.objects.select_related("role").filter(id=user_id)
    if role_name:
        query = query.filter(role__name=role_name)
    user = query.first()
    if not user or get_user_university_id(user) != university_id:
        return None
    return user


def _assert_payload_references_are_scoped(payload, *, university_id, list_context: str | None = None):
    """Reject IDs in report payloads that could resolve outside this university.

    This is deliberately strict for the identifiers understood by the PDF
    renderer.  Arbitrary display text remains allowed, but a client cannot
    sneak a foreign record into a nested ``cases``/``students`` list and make
    the export resolve it later.
    """
    if isinstance(payload, list):
        for item in payload:
            _assert_payload_references_are_scoped(item, university_id=university_id, list_context=list_context)
        return
    if not isinstance(payload, dict):
        return

    context = list_context
    for key, value in payload.items():
        if key in {"cases", "students", "supervisors", "patients", "items"} and isinstance(value, list):
            for item in value:
                _assert_payload_references_are_scoped(item, university_id=university_id, list_context=key)
            continue

        if key in {"case_id"} or (key == "id" and context == "cases"):
            if value and not Case.objects.filter(id=value, university_id=university_id).exists():
                raise ValidationError({key: "Referenced case is outside the report university."})
        elif key in {"student_id"} or (key == "id" and context == "students"):
            if value and not _scoped_user(value, university_id=university_id, role_name=Role.STUDENT):
                raise ValidationError({key: "Referenced student is outside the report university."})
        elif key in {"supervisor_id"} or (key == "id" and context == "supervisors"):
            if value and not _scoped_user(value, university_id=university_id, role_name=Role.SUPERVISOR):
                raise ValidationError({key: "Referenced supervisor is outside the report university."})
        elif key == "patient_id" or (key == "id" and context == "patients"):
            if value and not _scoped_user(value, university_id=university_id, role_name=Role.PATIENT):
                raise ValidationError({key: "Referenced patient is outside the report university."})
        elif isinstance(value, (dict, list)):
            _assert_payload_references_are_scoped(value, university_id=university_id, list_context=context)


def _assert_report_target_is_scoped(report: Report) -> None:
    """Fail closed for legacy/corrupt reports before rendering any medical data."""
    try:
        context = _get_target_context(report.target_type, report.target_id)
    except ValidationError as exc:
        raise PermissionDenied("Report target is no longer available.") from exc
    if context["university"].id != report.university_id:
        raise PermissionDenied("Report target is outside the report university.")
    snapshot = report.snapshot_data if isinstance(report.snapshot_data, dict) else {}
    if snapshot.get("university_id") and str(report.university_id) != str(snapshot["university_id"]):
        raise PermissionDenied("Report snapshot does not match the report university.")
    _assert_payload_references_are_scoped(report.content, university_id=report.university_id)
    _assert_payload_references_are_scoped(report.snapshot_data, university_id=report.university_id)


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

    _assert_payload_references_are_scoped(data.get("content"), university_id=university.id)
    # ``snapshot_data`` is intentionally not accepted from clients.  It is a
    # server-authored integrity anchor, not a second untrusted content field.

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
        snapshot_data=_server_snapshot(context),
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

    if "content" in data:
        _assert_payload_references_are_scoped(data["content"], university_id=report.university_id)

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

    _assert_report_target_is_scoped(report)

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
    if not supervisor_university_id or report.university_id != supervisor_university_id:
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
    if not supervisor_university_id or report.university_id != supervisor_university_id:
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


_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def _safe_text(value) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _format_date(value) -> str:
    if not value:
        return "-"
    try:
        if hasattr(value, "tzinfo") and value.tzinfo:
            value = timezone.localtime(value)
        return value.strftime("%Y-%m-%d")
    except Exception:
        return str(value)


def _calc_age(dob) -> str:
    if not dob:
        return "-"
    if isinstance(dob, date):
        today = timezone.localdate()
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return str(years)
    return "-"


def _get_profile(model, user):
    if not user:
        return None
    return model.objects.filter(user=user).first()


def _safe_get_user(user_id):
    if not user_id:
        return None
    try:
        return User.objects.filter(id=user_id).first()
    except Exception:
        return None


def _extract_value(keys, *sources):
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in keys:
            value = source.get(key)
            if value is not None and value != "":
                return value
    return None


def _extract_report_items(report: Report):
    content = report.content if isinstance(report.content, dict) else {}
    snapshot = report.snapshot_data if isinstance(report.snapshot_data, dict) else {}
    for key in ("cases", "students", "supervisors", "items"):
        items = content.get(key) or snapshot.get(key)
        if isinstance(items, list) and items:
            return key, items
    return None, []


def _resolve_case(report: Report, item):
    case_id = None
    if isinstance(item, dict):
        case_id = item.get("case_id") or item.get("id")
    if not case_id and report.target_type == Report.TargetType.CASE:
        case_id = report.target_id
    if not case_id and report.case_id:
        case_id = report.case_id
    if case_id:
        # Never resolve an identifier from report JSON without the report's
        # university predicate.  UUIDs are identifiers, not authorisation.
        return (
            Case.objects.select_related("student", "supervisor", "patient", "university")
            .filter(id=case_id, university_id=report.university_id)
            .first()
        )
    return None


def _resolve_student(report: Report, case, item):
    student_id = _extract_value(("student_id",), item)
    if student_id:
        return _scoped_user(student_id, university_id=report.university_id, role_name=Role.STUDENT)
    if case and case.student_id:
        return _scoped_user(case.student_id, university_id=report.university_id, role_name=Role.STUDENT)
    if report.student_id:
        return _scoped_user(report.student_id, university_id=report.university_id, role_name=Role.STUDENT)
    return None


def _resolve_supervisor(report: Report, case, item):
    supervisor_id = _extract_value(("supervisor_id",), item)
    if supervisor_id:
        return _scoped_user(supervisor_id, university_id=report.university_id, role_name=Role.SUPERVISOR)
    if case and case.supervisor_id:
        return _scoped_user(case.supervisor_id, university_id=report.university_id, role_name=Role.SUPERVISOR)
    if report.supervisor_id:
        return _scoped_user(report.supervisor_id, university_id=report.university_id, role_name=Role.SUPERVISOR)
    return None


def _resolve_patient(report: Report, case, item):
    patient_id = _extract_value(("patient_id",), item)
    if patient_id:
        return _scoped_user(patient_id, university_id=report.university_id, role_name=Role.PATIENT)
    if case and case.patient_id:
        return _scoped_user(case.patient_id, university_id=report.university_id, role_name=Role.PATIENT)
    return None


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
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    except Exception as exc:
        raise ValidationError({"format": "PDF export requires reportlab."}) from exc

    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        arabic_tools = True
    except Exception:
        arabic_tools = False

    content = report.content if isinstance(report.content, dict) else {}
    snapshot = report.snapshot_data if isinstance(report.snapshot_data, dict) else {}

    def _rtl(text: str) -> str:
        text = _safe_text(text)
        if arabic_tools and _ARABIC_RE.search(text):
            text = get_display(arabic_reshaper.reshape(text))
        return escape(text)

    def _resolve_path(path):
        if not path:
            return None
        candidate = Path(path)
        if not candidate.is_absolute():
            base_dir = getattr(settings, "BASE_DIR", None)
            if base_dir:
                candidate = Path(base_dir) / candidate
        return candidate if candidate.exists() else None

    def _register_fonts():
        font_name = "Helvetica"
        font_bold = "Helvetica-Bold"
        font_path = _resolve_path(getattr(settings, "REPORTS_PDF_FONT_PATH", None))
        bold_path = _resolve_path(getattr(settings, "REPORTS_PDF_BOLD_FONT_PATH", None))
        if font_path:
            pdfmetrics.registerFont(TTFont("ReportFont", str(font_path)))
            font_name = "ReportFont"
            font_bold = "ReportFont"
        if bold_path:
            pdfmetrics.registerFont(TTFont("ReportFontBold", str(bold_path)))
            font_bold = "ReportFontBold"
        return font_name, font_bold

    font_name, font_bold = _register_fonts()

    primary = colors.HexColor("#0B3C5D")
    light_gray = colors.HexColor("#E5E7EB")
    grid = colors.HexColor("#CBD5E1")

    title_style = ParagraphStyle(
        "Title",
        fontName=font_bold,
        fontSize=14,
        leading=18,
        alignment=2,
        textColor=primary,
    )
    label_style = ParagraphStyle(
        "Label",
        fontName=font_bold,
        fontSize=11,
        leading=14,
        alignment=2,
        textColor=primary,
    )
    value_style = ParagraphStyle(
        "Value",
        fontName=font_name,
        fontSize=11,
        leading=14,
        alignment=2,
    )
    small_style = ParagraphStyle(
        "Small",
        fontName=font_name,
        fontSize=9,
        leading=12,
        alignment=2,
    )

    def _kv_row(label, value):
        return [
            Paragraph(_rtl(value), value_style),
            Paragraph(_rtl(label), label_style),
        ]

    def _make_table(rows, doc_width):
        table = Table(rows, colWidths=[doc_width * 0.6, doc_width * 0.4])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (1, 0), (1, -1), light_gray),
                    ("TEXTCOLOR", (1, 0), (1, -1), primary),
                    ("GRID", (0, 0), (-1, -1), 0.5, grid),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _get_display_title():
        titles = {
            Report.ReportType.CLINICAL_CASE: "تقرير حالة طالب",
            Report.ReportType.SUPERVISOR_CASE_EVALUATION: "تقرير حالة مشرف",
            Report.ReportType.STUDENT_PERFORMANCE: "تقرير أداء طالب",
            Report.ReportType.COURSE_PERFORMANCE: "تقرير أداء مقرر",
            Report.ReportType.UNIVERSITY_STUDENTS: "تقرير طلبة الجامعة",
            Report.ReportType.UNIVERSITY_SUPERVISORS: "تقرير مشرفي الجامعة",
            Report.ReportType.UNIVERSITY_ARCHIVE: "تقرير أرشيف الجامعة",
        }
        return report.title or titles.get(report.report_type, "تقرير MediSmile")

    def _resolve_logo_paths():
        university_logo = None
        uni = report.university
        if uni and getattr(uni, "logo", None):
            try:
                candidate = Path(uni.logo.path)
                if candidate.exists():
                    university_logo = str(candidate)
            except Exception:
                university_logo = None

        medismile_logo = _resolve_path(getattr(settings, "REPORTS_MEDISMILE_LOGO", None))
        return university_logo, str(medismile_logo) if medismile_logo else None

    def _draw_header_footer(canvas, doc):
        canvas.saveState()
        width, height = A4
        uni_logo, ms_logo = _resolve_logo_paths()
        logo_size = 18 * mm
        header_top = height - 15 * mm
        if uni_logo:
            canvas.drawImage(
                uni_logo,
                doc.leftMargin,
                header_top - logo_size,
                width=logo_size,
                height=logo_size,
                preserveAspectRatio=True,
                mask="auto",
            )
        if ms_logo:
            canvas.drawImage(
                ms_logo,
                width - doc.rightMargin - logo_size,
                header_top - logo_size,
                width=logo_size,
                height=logo_size,
                preserveAspectRatio=True,
                mask="auto",
            )

        university_name = report.university.name if report.university_id else ""
        faculty_name = _extract_value(("faculty_name", "college"), content, snapshot)
        department_name = _extract_value(("department", "department_name"), content, snapshot)
        title = _get_display_title()

        center_y = height - 22 * mm
        canvas.setFont(font_bold, 12)
        for line in [university_name, faculty_name, department_name, title]:
            if not line:
                continue
            canvas.drawCentredString(width / 2, center_y, _rtl(line))
            center_y -= 5 * mm

        canvas.setStrokeColor(primary)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, height - 42 * mm, width - doc.rightMargin, height - 42 * mm)

        academic_year = _extract_value(("academic_year",), content, snapshot)
        if not academic_year:
            year = timezone.now().year
            academic_year = f"{year}/{year + 1}"

        footer_y = 12 * mm
        canvas.setStrokeColor(grid)
        canvas.setLineWidth(0.3)
        canvas.line(doc.leftMargin, footer_y + 8, width - doc.rightMargin, footer_y + 8)
        canvas.setFont(font_name, 9)
        canvas.drawString(doc.leftMargin, footer_y, "MediSmile")
        canvas.drawCentredString(width / 2, footer_y, _rtl(academic_year))
        canvas.drawRightString(width - doc.rightMargin, footer_y, _rtl(f"صفحة {canvas.getPageNumber()}"))
        canvas.setFont(font_name, 8)
        footer_statement = f"هذا التقرير أُعد لأغراض أكاديمية من الجامعة {university_name}"
        canvas.drawCentredString(width / 2, footer_y - 10, _rtl(footer_statement))
        canvas.restoreState()

    def _extract_ratings(item):
        case_rating = _extract_value(("case_rating", "case_score", "case_evaluation"), item, content, snapshot)
        student_rating = _extract_value(("student_rating", "student_score", "student_evaluation"), item, content, snapshot)
        supervisor_rating = _extract_value(("supervisor_rating", "supervisor_score", "supervisor_evaluation"), item, content, snapshot)
        if case_rating is None:
            case_rating = report.score
        return case_rating, student_rating, supervisor_rating

    def _build_student_case_rows(case, student_profile, item):
        student_name = _extract_value(("student_name", "student_full_name"), item, content, snapshot)
        if not student_name and case and case.student_id:
            student_name = case.student.get_full_name() or case.student.username
        if not student_name and report.student_id:
            student_name = report.student.get_full_name() or report.student.username

        rows = [
            _kv_row("اسم الطالب", student_name),
            _kv_row("الرقم الجامعي", getattr(student_profile, "student_id", None)),
            _kv_row("التخصص", getattr(student_profile, "specialization", None)),
            _kv_row("المرحلة الدراسية", getattr(student_profile, "year_of_study", None)),
            _kv_row("عنوان الحالة", _extract_value(("case_title", "title"), item) or getattr(case, "title", None) or report.title),
            _kv_row("وصف الحالة", _extract_value(("case_description", "description"), item, content, snapshot) or getattr(case, "description", None) or report.description),
            _kv_row("الإجراءات المتخذة", _extract_value(("actions_taken", "procedures", "actions"), item, content, snapshot)),
            _kv_row("تاريخ الإدخال", _format_date(getattr(case, "created_at", None) or report.created_at)),
            _kv_row("ملاحظات المشرف", _extract_value(("supervisor_notes", "notes"), item, content, snapshot) or report.review_notes),
        ]

        case_rating, student_rating, supervisor_rating = _extract_ratings(item)
        rows.extend(
            [
                _kv_row("تقييم الحالة", case_rating),
                _kv_row("تقييم الطالب", student_rating),
                _kv_row("تقييم المشرف", supervisor_rating),
            ]
        )
        return rows

    def _build_supervisor_case_rows(supervisor_profile, item):
        supervisor_name = _extract_value(("supervisor_name", "supervisor_full_name"), item, content, snapshot)
        supervisor = _resolve_supervisor(report, None, item)
        if not supervisor_name and supervisor:
            supervisor_name = supervisor.get_full_name() or supervisor.username

        rows = [
            _kv_row("اسم المشرف", supervisor_name),
            _kv_row("الدرجة العلمية", getattr(supervisor_profile, "position", None)),
            _kv_row("القسم", getattr(supervisor_profile, "department", None)),
            _kv_row("نوع الحالة", _extract_value(("case_type",), item, content, snapshot) or "أكاديمية"),
            _kv_row("تفاصيل الحالة", _extract_value(("case_details", "details"), item, content, snapshot) or report.description),
            _kv_row("التوصيات", _extract_value(("recommendations",), item, content, snapshot) or report.review_notes),
            _kv_row("تاريخ التقرير", _format_date(report.created_at)),
        ]
        case_rating, student_rating, supervisor_rating = _extract_ratings(item)
        rows.extend(
            [
                _kv_row("تقييم الحالة", case_rating),
                _kv_row("تقييم الطالب", student_rating),
                _kv_row("تقييم المشرف", supervisor_rating),
            ]
        )
        return rows

    def _build_patient_case_rows(case, patient_profile, item):
        patient_name = _extract_value(("patient_name",), item, content, snapshot)
        mask_name = _extract_value(("mask_patient_name", "patient_name_masked", "anonymize_patient"), item, content, snapshot)
        if mask_name:
            patient_name = "مخفي"
        if not patient_name and case and case.patient_id:
            patient = case.patient
            patient_name = patient.get_full_name() or patient.username

        rows = [
            _kv_row("رقم الحالة", getattr(case, "id", None) or report.target_id),
            _kv_row("اسم المريض", patient_name),
            _kv_row("العمر", _calc_age(getattr(patient_profile, "date_of_birth", None))),
            _kv_row("الجنس", getattr(patient_profile, "gender", None)),
            _kv_row("التشخيص", _extract_value(("diagnosis",), item, content, snapshot) or getattr(case, "title", None)),
            _kv_row("الخطة العلاجية", _extract_value(("treatment_plan",), item, content, snapshot)),
            _kv_row("المتابعة", _extract_value(("follow_up", "followup"), item, content, snapshot)),
            _kv_row("ملاحظات طبية", _extract_value(("medical_notes", "notes"), item, content, snapshot) or report.description),
            _kv_row("تاريخ التقرير", _format_date(report.created_at)),
        ]
        case_rating, student_rating, supervisor_rating = _extract_ratings(item)
        rows.extend(
            [
                _kv_row("تقييم الحالة", case_rating),
                _kv_row("تقييم الطالب", student_rating),
                _kv_row("تقييم المشرف", supervisor_rating),
            ]
        )
        return rows

    def _build_student_performance_rows(student_profile, item):
        student_name = _extract_value(("student_name", "student_full_name"), item, content, snapshot)
        student = _resolve_student(report, None, item)
        if not student_name and student:
            student_name = student.get_full_name() or student.username

        rows = [
            _kv_row("اسم الطالب", student_name),
            _kv_row("الرقم الجامعي", getattr(student_profile, "student_id", None)),
            _kv_row("التخصص", getattr(student_profile, "specialization", None)),
            _kv_row("المرحلة الدراسية", getattr(student_profile, "year_of_study", None)),
            _kv_row("عدد الحالات", _extract_value(("cases_count", "total_cases"), item, content, snapshot)),
            _kv_row("متوسط تقييم الحالات", _extract_value(("case_avg", "cases_avg"), item, content, snapshot)),
            _kv_row("متوسط تقييم الطالب", _extract_value(("student_avg", "student_rating"), item, content, snapshot)),
            _kv_row("ملاحظات المشرف", _extract_value(("notes", "supervisor_notes"), item, content, snapshot) or report.review_notes),
        ]
        return rows

    def _build_generic_rows():
        return [
            _kv_row("محتوى التقرير", _render_report_text(report)),
        ]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=48 * mm,
        bottomMargin=28 * mm,
    )

    story = []
    items_key, items = _extract_report_items(report)
    total_items = len(items) if items else 1

    def _append_section(title, rows, is_last):
        story.append(Paragraph(_rtl(title), title_style))
        story.append(Spacer(1, 8))
        story.append(_make_table(rows, doc.width))
        if not is_last:
            story.append(PageBreak())

    if items:
        for idx, item in enumerate(items):
            case = _resolve_case(report, item)
            student = _resolve_student(report, case, item)
            supervisor = _resolve_supervisor(report, case, item)
            patient = _resolve_patient(report, case, item)
            student_profile = _get_profile(StudentProfile, student)
            supervisor_profile = _get_profile(SupervisorProfile, supervisor)
            patient_profile = _get_profile(PatientProfile, patient)

            if items_key == "students":
                rows = _build_student_performance_rows(student_profile, item)
                title = f"تقرير أداء طالب - {idx + 1}"
            elif items_key == "supervisors":
                rows = _build_supervisor_case_rows(supervisor_profile, item)
                title = f"تقرير حالة مشرف - {idx + 1}"
            else:
                if report.report_type == Report.ReportType.CLINICAL_CASE:
                    rows = _build_student_case_rows(case, student_profile, item)
                    title = f"تقرير حالة طالب - {idx + 1}"
                elif report.report_type == Report.ReportType.SUPERVISOR_CASE_EVALUATION:
                    rows = _build_supervisor_case_rows(supervisor_profile, item)
                    title = f"تقرير حالة مشرف - {idx + 1}"
                else:
                    rows = _build_patient_case_rows(case, patient_profile, item)
                    title = f"تقرير حالة مريض - {idx + 1}"

            _append_section(title, rows, idx == total_items - 1)
    else:
        case = _resolve_case(report, None)
        student = _resolve_student(report, case, None)
        supervisor = _resolve_supervisor(report, case, None)
        patient = _resolve_patient(report, case, None)
        student_profile = _get_profile(StudentProfile, student)
        supervisor_profile = _get_profile(SupervisorProfile, supervisor)
        patient_profile = _get_profile(PatientProfile, patient)

        if report.report_type == Report.ReportType.CLINICAL_CASE:
            rows = _build_student_case_rows(case, student_profile, None)
            title = "تقرير حالة طالب"
        elif report.report_type == Report.ReportType.SUPERVISOR_CASE_EVALUATION:
            rows = _build_supervisor_case_rows(supervisor_profile, None)
            title = "تقرير حالة مشرف"
        elif report.target_type == Report.TargetType.CASE:
            rows = _build_patient_case_rows(case, patient_profile, None)
            title = "تقرير حالة مريض"
        elif report.target_type == Report.TargetType.STUDENT:
            rows = _build_student_performance_rows(student_profile, None)
            title = "تقرير أداء طالب"
        else:
            rows = _build_generic_rows()
            title = _get_display_title()

        _append_section(title, rows, True)

    doc.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)
    return buffer.getvalue()


def export_report(*, actor, report: Report, fmt: str) -> str:
    if actor.role.name != Role.UNIVERSITY_ADMIN:
        raise PermissionDenied("Only University Admin can export reports.")

    admin_university_id = _resolve_university_id(actor)
    if not admin_university_id or report.university_id != admin_university_id:
        raise PermissionDenied("You cannot export reports outside your university.")

    # Re-run all scope checks immediately before each rendering. This protects
    # legacy reports created before the validation above and guards against
    # records that changed university after the report was drafted.
    _assert_report_target_is_scoped(report)

    fmt = (fmt or "").lower()
    if fmt == "excel":
        fmt = "csv"
    if fmt not in {"csv", "pdf"}:
        raise ValidationError({"format": "Invalid export format. Use pdf, excel, or csv."})

    exports_dir = Path(settings.PRIVATE_MEDIA_ROOT) / "exports"
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

    # Medical exports are never published under /media/.  They are served by
    # an authenticated, university-scoped endpoint.
    report.file_url = f"/api/reports/{report.id}/export-file/"
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


def get_export_file_path(report: Report) -> Path | None:
    """Return a report export from private storage, never from a request path."""
    exports_dir = Path(settings.PRIVATE_MEDIA_ROOT) / "exports"
    for suffix in ("pdf", "csv"):
        candidate = exports_dir / f"report_{report.id}.{suffix}"
        if candidate.is_file():
            return candidate
    return None
