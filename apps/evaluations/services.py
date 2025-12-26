# apps/evaluations/services.py
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.cases.models import Case, CaseSession
from apps.appointments.models import Appointment

from .models import Evaluation, EvaluationStatus, EvaluationTargetType


def create_evaluation(*, actor, data: dict) -> Evaluation:
    role_name = getattr(getattr(actor, "role", None), "name", None)
    if role_name not in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        raise PermissionDenied("Only supervisors or university admins can create evaluations.")

    student: User = data["student"]
    target_type = data["target_type"]
    score = data["score"]
    rubric = data.get("rubric") or {}
    comment = data.get("comment") or ""

    case = data.get("case")
    session = data.get("session")
    appointment = data.get("appointment")

    # Duplicate prevention: evaluator+student+target exact
    dup = Evaluation.objects.filter(
        evaluator=actor,
        student=student,
        target_type=target_type,
    )
    if target_type == EvaluationTargetType.CASE:
        dup = dup.filter(case=case)
    elif target_type == EvaluationTargetType.SESSION:
        dup = dup.filter(session=session)
    elif target_type == EvaluationTargetType.APPOINTMENT:
        dup = dup.filter(appointment=appointment)
    if dup.exists():
        raise PermissionDenied("Evaluation already exists for this target by the same evaluator.")

    evaluation = Evaluation.objects.create(
        university=data["university"],
        evaluator=actor,
        student=student,
        target_type=target_type,
        case=case,
        session=session,
        appointment=appointment,
        status=EvaluationStatus.DRAFT,
        score=score,
        rubric=rubric,
        comment=comment,
    )
    return evaluation


def update_evaluation(*, actor, evaluation: Evaluation, data: dict) -> Evaluation:
    if evaluation.is_locked:
        raise PermissionDenied("Final evaluations are locked.")

    role_name = getattr(getattr(actor, "role", None), "name", None)
    if role_name == Role.SUPERVISOR and evaluation.evaluator_id != actor.id:
        raise PermissionDenied("Only the evaluator can update this evaluation.")
    if role_name == Role.UNIVERSITY_ADMIN:
        if evaluation.university_id not in _get_user_university_ids(actor):
            raise PermissionDenied("Out of university scope.")
    if role_name not in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        raise PermissionDenied("Not allowed.")

    for f in ("score", "rubric", "comment"):
        if f in data:
            setattr(evaluation, f, data[f])
    evaluation.save(update_fields=["score", "rubric", "comment", "updated_at"])
    return evaluation


def submit_evaluation(*, actor, evaluation: Evaluation) -> Evaluation:
    _assert_can_change_status(actor, evaluation)
    evaluation.status = EvaluationStatus.SUBMITTED
    evaluation.submitted_at = timezone.now()
    evaluation.save(update_fields=["status", "submitted_at", "updated_at"])
    return evaluation


def finalize_evaluation(*, actor, evaluation: Evaluation) -> Evaluation:
    _assert_can_change_status(actor, evaluation)
    evaluation.status = EvaluationStatus.FINAL
    evaluation.finalized_at = timezone.now()
    evaluation.save(update_fields=["status", "finalized_at", "updated_at"])
    return evaluation


def _assert_can_change_status(actor, evaluation: Evaluation):
    if evaluation.is_locked:
        raise PermissionDenied("Final evaluations are locked.")

    role_name = getattr(getattr(actor, "role", None), "name", None)
    if role_name == Role.SUPERVISOR and evaluation.evaluator_id != actor.id:
        raise PermissionDenied("Only evaluator can change status.")
    if role_name == Role.UNIVERSITY_ADMIN:
        if evaluation.university_id not in _get_user_university_ids(actor):
            raise PermissionDenied("Out of university scope.")
    if role_name not in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        raise PermissionDenied("Not allowed.")


def _get_user_university_ids(user) -> set:
    ids = set()
    if getattr(user, "university_id", None):
        ids.add(user.university_id)
    rel = getattr(user, "universities", None)
    if rel is not None and hasattr(rel, "all"):
        ids |= set(rel.values_list("id", flat=True))
    return ids
