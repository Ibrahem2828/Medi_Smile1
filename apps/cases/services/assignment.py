# apps/cases/services/assignment.py

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.cases.models import (
    Case,
    CaseAssignmentRequest,
    CaseHistory,
)


@transaction.atomic
def request_case_assignment(*, case: Case, student: User, message: str = "") -> CaseAssignmentRequest:
    """
    Student requests to be assigned to a public case.
    """

    if student.role != "student":
        raise ValidationError(_("Only students can request case assignment."))

    if not case.is_public or case.status != Case.Status.PENDING_ASSIGNMENT:
        raise ValidationError(_("This case is not open for assignment."))

    if CaseAssignmentRequest.objects.filter(case=case, student=student).exists():
        raise ValidationError(_("Assignment request already exists."))

    assignment = CaseAssignmentRequest.objects.create(
        case=case,
        student=student,
        message=message,
    )

    CaseHistory.objects.create(
        case=case,
        action=CaseHistory.Action.ASSIGNMENT_REQUESTED,
        description=_("Student requested assignment."),
        performed_by=student,
    )

    return assignment


@transaction.atomic
def decide_assignment_request(
    *,
    assignment: CaseAssignmentRequest,
    supervisor: User,
    accept: bool,
    response: str = "",
) -> Case:
    """
    Supervisor accepts or rejects assignment request.
    """

    if supervisor.role != "supervisor":
        raise ValidationError(_("Only supervisors can decide assignment requests."))

    if assignment.status != CaseAssignmentRequest.Status.PENDING:
        raise ValidationError(_("This assignment request is already processed."))

    assignment.supervisor_response = response

    if accept:
        assignment.status = CaseAssignmentRequest.Status.ACCEPTED

        case = assignment.case
        case.student = assignment.student
        case.supervisor = supervisor
        case.status = Case.Status.ASSIGNED
        case.is_public = False
        case.save()

        CaseHistory.objects.create(
            case=case,
            action=CaseHistory.Action.ASSIGNED,
            description=_("Case assigned to student."),
            performed_by=supervisor,
        )

    else:
        assignment.status = CaseAssignmentRequest.Status.REJECTED

        CaseHistory.objects.create(
            case=assignment.case,
            action=CaseHistory.Action.STATUS_CHANGED,
            description=_("Assignment request rejected."),
            performed_by=supervisor,
        )

    assignment.save()
    return assignment.case
