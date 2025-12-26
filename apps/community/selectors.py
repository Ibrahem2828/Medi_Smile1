# apps/community/selectors.py
from django.db.models import Count, Avg
from apps.accounts.models import Role
from apps.evaluations.models import Evaluation, EvaluationStatus
from .models import Content, ContentLike, ContentComment


# ============================================================
# Content Feed
# ============================================================

def content_queryset_for_user(user):
    qs = (
        Content.objects
        .select_related("author", "university", "approved_by")
        .annotate(
            likes_count=Count("likes", distinct=True),
            comments_count=Count("comments", distinct=True),
        )
        .order_by("-created_at")
    )

    role = getattr(getattr(user, "role", None), "name", None)

    if not user.is_authenticated:
        return qs.none()

    # Tech Support → all approved
    if role == Role.TECH_SUPPORT:
        return qs.filter(status=Content.Status.APPROVED)

    # Patient → public only
    if role == Role.PATIENT:
        return qs.filter(
            status=Content.Status.APPROVED,
            is_public=True,
        )

    # Students / Supervisors / University Admins
    return (
        qs.filter(status=Content.Status.APPROVED, is_public=True)
        | qs.filter(
            status=Content.Status.APPROVED,
            university_id=user.university_id,
        )
    )


# ============================================================
# Moderation
# ============================================================

def pending_content_for_moderator(user):
    role = getattr(getattr(user, "role", None), "name", None)

    if role == Role.TECH_SUPPORT:
        return Content.objects.filter(status=Content.Status.PENDING)

    if role in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        return Content.objects.filter(
            status=Content.Status.PENDING,
            university_id=user.university_id,
        )

    return Content.objects.none()


# ============================================================
# Interactions
# ============================================================

def has_liked(content, user) -> bool:
    return ContentLike.objects.filter(content=content, user=user).exists()


# ============================================================
# ⭐ Student Public Rating
# ============================================================

def student_public_rating(student):
    qs = Evaluation.objects.filter(
        student=student,
        status=EvaluationStatus.FINAL,
    )

    if not qs.exists():
        return {
            "student_id": str(student.id),
            "average_score": None,
            "stars": 0,
            "total_evaluations": 0,
        }

    avg_score = qs.aggregate(avg=Avg("score"))["avg"] or 0

    if avg_score <= 20:
        stars = 1
    elif avg_score <= 40:
        stars = 2
    elif avg_score <= 60:
        stars = 3
    elif avg_score <= 80:
        stars = 4
    else:
        stars = 5

    return {
        "student_id": str(student.id),
        "average_score": round(avg_score, 2),
        "stars": stars,
        "total_evaluations": qs.count(),
    }
