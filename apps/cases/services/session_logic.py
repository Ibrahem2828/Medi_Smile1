# apps/cases/services/session_logic.py

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.cases.models import (
    Case,
    CaseSession,
    CaseHistory,
)


@transaction.atomic
def create_session(*, case: Case, student: User, notes: str) -> CaseSession:
    """
    Student creates a treatment session.
    """

    if student.role != "student":
        raise ValidationError(_("Only students can create sessions."))

    if case.student != student:
        raise ValidationError(_("You are not assigned to this case."))

    if case.status not in {Case.Status.ASSIGNED, Case.Status.IN_PROGRESS}:
        raise ValidationError(_("Cannot create session for this case status."))

    session = CaseSession.objects.create(
        case=case,
        student=student,
        supervisor=case.supervisor,
        notes=notes,
        status=CaseSession.Status.COMPLETED,
    )

    case.status = Case.Status.IN_PROGRESS
    case.save()

    CaseHistory.objects.create(
        case=case,
        action=CaseHistory.Action.SESSION_CREATED,
        description=_("Treatment session created."),
        performed_by=student,
    )

    return session


@transaction.atomic
def review_session(
    *,
    session: CaseSession,
    supervisor: User,
    approve: bool,
    feedback: str = "",
) -> CaseSession:
    """
    Supervisor reviews a treatment session.
    """

    if supervisor.role != "supervisor":
        raise ValidationError(_("Only supervisors can review sessions."))

    if session.supervisor != supervisor:
        raise ValidationError(_("You are not assigned to this session."))

    if session.status not in {
        CaseSession.Status.COMPLETED,
        CaseSession.Status.NEEDS_REVIEW,
    }:
        raise ValidationError(_("This session cannot be reviewed."))

    session.supervisor_feedback = feedback

    if approve:
        session.status = CaseSession.Status.APPROVED
    else:
        session.status = CaseSession.Status.REJECTED

    session.save()

    CaseHistory.objects.create(
        case=session.case,
        action=CaseHistory.Action.SESSION_REVIEWED,
        description=_("Session reviewed by supervisor."),
        performed_by=supervisor,
    )

    return session
