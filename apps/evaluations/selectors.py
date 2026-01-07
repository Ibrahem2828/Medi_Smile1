# apps/evaluations/selectors.py
from django.db.models import Avg, Count, Q

from apps.accounts.models import Role
from .models import Evaluation, EvaluationStatus, EvaluationTargetType


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


def evaluations_queryset_for_user(user):
    qs = Evaluation.objects.select_related(
        "university",
        "evaluator",
        "student",
        "case",
        "session",
        "appointment",
    ).prefetch_related("adjustments")

    role_name = getattr(getattr(user, "role", None), "name", None)

    if role_name == Role.PATIENT:
        return qs.filter(evaluator=user)

    if role_name == Role.STUDENT:
        return qs.filter(Q(evaluator=user) | Q(student=user))

    if role_name in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        uni_ids = _get_user_university_ids(user)
        return qs.filter(university_id__in=uni_ids)

    return qs.none()


def student_statistics(student):
    qs = Evaluation.objects.filter(student=student)

    total = qs.count()
    if total == 0:
        return {
            "student_id": str(student.id),
            "student_name": student.get_full_name() or student.username,
            "average_score": None,
            "total_evaluations": 0,
            "by_status": {k: 0 for k, _ in EvaluationStatus.choices},
        }

    avg = qs.aggregate(avg=Avg("final_score"))["avg"]
    return {
        "student_id": str(student.id),
        "student_name": student.get_full_name() or student.username,
        "average_score": round(avg, 2) if avg is not None else None,
        "total_evaluations": total,
        "by_status": {k: qs.filter(status=k).count() for k, _ in EvaluationStatus.choices},
    }


def student_rating(student):
    weights = {
        Role.PATIENT: 0.35,
        Role.SUPERVISOR: 0.45,
        Role.UNIVERSITY_ADMIN: 0.20,
    }

    qs = Evaluation.objects.filter(
        target_type=EvaluationTargetType.STUDENT,
        target_id=student.id,
        status=EvaluationStatus.FINALIZED,
    )

    if not qs.exists():
        return {
            "student_id": str(student.id),
            "final_rating": None,
            "total_evaluations": 0,
            "components": {},
        }

    role_groups = (
        qs.values("evaluator_role")
        .annotate(avg=Avg("final_score"), count=Count("id"))
    )

    components = {}
    weighted_sum = 0.0
    weight_total = 0.0
    total = 0

    for row in role_groups:
        role = row["evaluator_role"]
        avg_score = row["avg"] or 0
        count = row["count"] or 0
        total += count
        components[role] = {
            "average": round(avg_score, 2),
            "count": count,
            "weight": weights.get(role, 0),
        }
        if role in weights:
            weighted_sum += avg_score * weights[role]
            weight_total += weights[role]

    final_rating = weighted_sum / weight_total if weight_total else None

    return {
        "student_id": str(student.id),
        "final_rating": round(final_rating, 2) if final_rating is not None else None,
        "total_evaluations": total,
        "components": components,
    }
