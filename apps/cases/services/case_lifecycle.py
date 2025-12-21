# apps/cases/services/case_lifecycle.py

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.cases.models import Case, CaseHistory
from apps.accounts.models import User


@transaction.atomic
def change_case_status(*, case: Case, new_status: str, actor: User):
    """
    Safely change case status with full validation and history logging.
    """

    if case.status == Case.Status.CLOSED:
        raise ValidationError(_("Closed cases cannot be modified."))

    allowed_roles = {"student", "supervisor"}
    if actor.role not in allowed_roles:
        raise ValidationError(_("You are not allowed to change case status."))

    old_status = case.status
    case.status = new_status
    case.save()

    CaseHistory.objects.create(
        case=case,
        action=CaseHistory.Action.STATUS_CHANGED,
        description=_(
            f"Case status changed from {old_status} to {new_status}."
        ),
        performed_by=actor,
    )

    return case


@transaction.atomic
def close_case(*, case: Case, supervisor: User):
    """
    Final closure of a case (supervisor only).
    """

    if supervisor.role != "supervisor":
        raise ValidationError(_("Only supervisors can close cases."))

    if case.status != Case.Status.COMPLETED:
        raise ValidationError(_("Only completed cases can be closed."))

    case.status = Case.Status.CLOSED
    case.save()

    CaseHistory.objects.create(
        case=case,
        action=CaseHistory.Action.CLOSED,
        description=_("Case closed and finalized."),
        performed_by=supervisor,
    )

    return case
