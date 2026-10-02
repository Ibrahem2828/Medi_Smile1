# apps/evaluations/services.py
import logging

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.utils import timezone

from apps.accounts.models import Role
from apps.appointments.models import Appointment
from apps.audit.services import log_audit_event
from apps.cases.models import Case, CaseSession

from .models import (
    Evaluation,
    EvaluationAdjustment,
    EvaluationStatus,
    EvaluationTargetType,
)

logger = logging.getLogger(__name__)


def _resolve_university_id(user):
    if not user:
        return None

    for attr in (
        "studentprofile_profile",
        "supervisorprofile_profile",
        "universityadminprofile_profile",
        "patientprofile_profile",
    ):
        try:
            profile = getattr(user, attr, None)
        except Exception:
            profile = None
        uni_id = getattr(profile, "university_id", None)
        if uni_id:
            return uni_id
    return None


def _get_user_university_ids(user) -> set:
    ids = set()
    uni_id = _resolve_university_id(user)
    if uni_id:
        ids.add(uni_id)
    rel = getattr(user, "universities", None)
    if rel is not None and hasattr(rel, "all"):
        ids |= set(rel.values_list("id", flat=True))
    return ids


def create_evaluation(*, actor, data: dict) -> Evaluation:
    role_name = getattr(getattr(actor, "role", None), "name", None)
    target_type = data["target_type"]

    case = data.get("case")
    session = data.get("session")
    appointment = data.get("appointment")
    target_user = data.get("target_user")

    # Role rules
    if role_name == Role.PATIENT:
        if target_type not in {EvaluationTargetType.APPOINTMENT, EvaluationTargetType.STUDENT}:
            raise PermissionDenied("Patients can only evaluate appointments or students.")
    elif role_name == Role.STUDENT:
        if target_type != EvaluationTargetType.CASE:
            raise PermissionDenied("Students can only evaluate cases.")
        if not case:
            raise DjangoValidationError({"target_id": "Case is required for student evaluation."})
        if case.student_id != actor.id:
            raise PermissionDenied("You can only evaluate your own cases.")
    elif role_name == Role.SUPERVISOR:
        if target_type not in {
            EvaluationTargetType.STUDENT,
            EvaluationTargetType.CASE,
            EvaluationTargetType.SESSION,
            EvaluationTargetType.APPOINTMENT,
        }:
            raise PermissionDenied("Supervisors can only evaluate students, cases, sessions, or appointments.")
    elif role_name == Role.UNIVERSITY_ADMIN:
        if target_type not in {EvaluationTargetType.STUDENT, EvaluationTargetType.SUPERVISOR}:
            raise PermissionDenied("University admins can only evaluate students or supervisors.")
    else:
        raise PermissionDenied("You are not allowed to create evaluations.")

    # Target resolution
    student = None
    target_id = data.get("target_id")

    if target_type == EvaluationTargetType.CASE:
        if not case:
            raise DjangoValidationError({"target_id": "Case not found."})
        target_id = case.id
        student = case.student
    elif target_type == EvaluationTargetType.SESSION:
        if not session:
            raise DjangoValidationError({"target_id": "Session not found."})
        target_id = session.id
        student = session.student
        case = session.case
    elif target_type == EvaluationTargetType.APPOINTMENT:
        if not appointment:
            raise DjangoValidationError({"target_id": "Appointment not found."})
        target_id = appointment.id
        student = appointment.student
        case = appointment.case
        if role_name == Role.PATIENT and appointment.patient_id != actor.id:
            raise PermissionDenied("You can only evaluate your own appointments.")
    elif target_type == EvaluationTargetType.STUDENT:
        student = target_user
        if not student:
            raise DjangoValidationError({"target_id": "Student not found."})
        target_id = student.id
    elif target_type == EvaluationTargetType.SUPERVISOR:
        if not target_user:
            raise DjangoValidationError({"target_id": "Supervisor not found."})
        target_id = target_user.id
    else:
        raise DjangoValidationError({"target_type": "Invalid target type."})

    if not target_id:
        raise DjangoValidationError({"target_id": "Target id is required."})

    if role_name == Role.SUPERVISOR and target_type in {
        EvaluationTargetType.CASE,
        EvaluationTargetType.SESSION,
        EvaluationTargetType.APPOINTMENT,
    }:
        supervisor_id = None
        if session and session.supervisor_id:
            supervisor_id = session.supervisor_id
        if not supervisor_id and appointment and appointment.supervisor_id:
            supervisor_id = appointment.supervisor_id
        if not supervisor_id and case and case.supervisor_id:
            supervisor_id = case.supervisor_id
        if supervisor_id != actor.id:
            raise PermissionDenied("You can only evaluate cases, sessions, or appointments you supervise.")

    # University scope
    university_id = None
    if case and case.university_id:
        university_id = case.university_id
    if not university_id and appointment and appointment.case and appointment.case.university_id:
        university_id = appointment.case.university_id
    if not university_id and student:
        university_id = _resolve_university_id(student)
    if not university_id and target_user:
        university_id = _resolve_university_id(target_user)
    if not university_id:
        raise DjangoValidationError("University could not be resolved for this evaluation.")

    if role_name == Role.PATIENT and target_type == EvaluationTargetType.STUDENT:
        # A patient may rate only a student who has actually treated one of
        # their cases.  A patient profile can legitimately be created before
        # a university is selected, so ownership of this treatment relation
        # (rather than a nullable profile field) is the security boundary.
        if not Case.objects.filter(patient=actor, student=student, university_id=university_id).exists():
            raise PermissionDenied("You can only evaluate a student assigned to your case.")

    actor_university_id = _resolve_university_id(actor)
    if role_name in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        # A missing profile is never a wildcard.  The old ``if university_id
        # and ...`` pattern let an unscoped administrator evaluate another
        # university's student.
        if not actor_university_id or actor_university_id != university_id:
            raise PermissionDenied("Out of university scope.")
    elif role_name == Role.PATIENT and actor_university_id and actor_university_id != university_id:
        # If the patient has selected a university, it too must match.  If it
        # is null, the appointment/case ownership checks above still prevent
        # a cross-university evaluation.
        raise PermissionDenied("Out of university scope.")

    if Evaluation.objects.filter(
        evaluator=actor,
        target_type=target_type,
        target_id=target_id,
    ).exists():
        raise DjangoValidationError("Evaluation already exists for this target.")

    status = EvaluationStatus.UNDER_REVIEW if role_name in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN} else EvaluationStatus.CREATED
    submitted_at = timezone.now() if status == EvaluationStatus.UNDER_REVIEW else None

    evaluation = Evaluation.objects.create(
        university_id=university_id,
        evaluator=actor,
        evaluator_role=role_name,
        student=student,
        target_type=target_type,
        target_id=target_id,
        case=case if target_type == EvaluationTargetType.CASE else None,
        session=session if target_type == EvaluationTargetType.SESSION else None,
        appointment=appointment if target_type == EvaluationTargetType.APPOINTMENT else None,
        status=status,
        score=data["score"],
        final_score=data["score"],
        rubric=data.get("rubric") or {},
        comment=data.get("comment") or "",
        submitted_at=submitted_at,
    )

    log_audit_event(
        user=actor,
        university=evaluation.university,
        action="evaluations.created",
        description="Evaluation created",
        content_object=evaluation,
        metadata={"target_type": evaluation.target_type, "target_id": str(evaluation.target_id)},
    )

    return evaluation


def adjust_evaluation(*, actor, evaluation: Evaluation, new_score: int, reason: str) -> Evaluation:
    if evaluation.is_locked:
        raise PermissionDenied("Finalized evaluations are locked.")

    role_name = getattr(getattr(actor, "role", None), "name", None)
    if role_name not in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        raise PermissionDenied("Only supervisors or university admins can adjust evaluations.")

    if evaluation.university_id not in _get_user_university_ids(actor):
        raise PermissionDenied("Out of university scope.")

    if not reason:
        raise DjangoValidationError({"reason": "Adjustment reason is required."})

    old_score = evaluation.final_score if evaluation.final_score is not None else evaluation.score

    EvaluationAdjustment.objects.create(
        evaluation=evaluation,
        adjusted_by=actor,
        adjusted_role=role_name,
        old_score=old_score,
        new_score=new_score,
        reason=reason,
    )

    evaluation.final_score = new_score
    evaluation.status = EvaluationStatus.ADJUSTED
    evaluation.save(update_fields=["final_score", "status", "updated_at"])

    log_audit_event(
        user=actor,
        university=evaluation.university,
        action="evaluations.adjusted",
        description="Evaluation adjusted",
        content_object=evaluation,
        metadata={"old_score": old_score, "new_score": new_score, "reason": reason},
    )

    return evaluation


def finalize_evaluation(*, actor, evaluation: Evaluation) -> Evaluation:
    if evaluation.is_locked:
        raise PermissionDenied("Evaluation already finalized.")

    role_name = getattr(getattr(actor, "role", None), "name", None)
    if role_name != Role.UNIVERSITY_ADMIN:
        raise PermissionDenied("Only university admins can finalize evaluations.")

    if evaluation.university_id not in _get_user_university_ids(actor):
        raise PermissionDenied("Out of university scope.")

    if evaluation.final_score is None:
        evaluation.final_score = evaluation.score

    evaluation.status = EvaluationStatus.FINALIZED
    evaluation.finalized_at = timezone.now()
    evaluation.save(update_fields=["final_score", "status", "finalized_at", "updated_at"])

    log_audit_event(
        user=actor,
        university=evaluation.university,
        action="evaluations.finalized",
        description="Evaluation finalized",
        content_object=evaluation,
        metadata={"final_score": evaluation.final_score},
    )

    return evaluation
