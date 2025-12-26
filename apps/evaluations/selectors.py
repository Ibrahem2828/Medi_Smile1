# apps/evaluations/selectors.py
from django.db.models import Avg
from apps.accounts.models import Role
from .models import Evaluation, EvaluationStatus


def evaluations_queryset_for_user(user):
    qs = Evaluation.objects.select_related(
        "university",
        "evaluator",
        "student",
        "case",
        "session",
        "appointment",
    )

    role_name = getattr(getattr(user, "role", None), "name", None)

    if role_name == Role.STUDENT:
        return qs.filter(student=user)

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

    avg = qs.aggregate(avg=Avg("score"))["avg"]
    return {
        "student_id": str(student.id),
        "student_name": student.get_full_name() or student.username,
        "average_score": round(avg, 2) if avg is not None else None,
        "total_evaluations": total,
        "by_status": {k: qs.filter(status=k).count() for k, _ in EvaluationStatus.choices},
    }


def _get_user_university_ids(user) -> set:
    ids = set()
    if getattr(user, "university_id", None):
        ids.add(user.university_id)
    rel = getattr(user, "universities", None)
    if rel is not None and hasattr(rel, "all"):
        ids |= set(rel.values_list("id", flat=True))
    return ids
    