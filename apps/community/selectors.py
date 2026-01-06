# apps/community/selectors.py
from django.db.models import Count, Avg

from apps.accounts.models import Role
from apps.evaluations.models import Evaluation, EvaluationStatus
from .models import Content, ContentLike, ContentComment


# ============================================================
# Helpers
# ============================================================

def _resolve_university_id(user):
    """
    Safely fetch a university id from available profiles, avoiding AttributeError.
    """
    if not user:
        return None

    for attr in ("studentprofile_profile", "supervisorprofile_profile", "universityadminprofile_profile"):
        try:
            profile = getattr(user, attr, None)
        except Exception:
            profile = None
        uni_id = getattr(profile, "university_id", None)
        if uni_id:
            return uni_id
    return None


# ============================================================
# Content Feed
# ============================================================

def content_queryset_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return Content.objects.none()

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

    # Tech Support: all approved
    if role == Role.TECH_SUPPORT:
        return qs.filter(status=Content.Status.APPROVED)

    # Patient: public only
    if role == Role.PATIENT:
        return qs.filter(
            status=Content.Status.APPROVED,
            is_public=True,
        )

    # Students / Supervisors / University Admins
    uni_id = _resolve_university_id(user)
    public_qs = qs.filter(status=Content.Status.APPROVED, is_public=True)
    if not uni_id:
        return public_qs

    return (
        public_qs
        | qs.filter(
            status=Content.Status.APPROVED,
            university_id=uni_id,
        )
    )


# ============================================================
# Moderation
# ============================================================

def pending_content_for_moderator(user):
    if not user or not getattr(user, "is_authenticated", False):
        return Content.objects.none()

    role = getattr(getattr(user, "role", None), "name", None)

    if role == Role.TECH_SUPPORT:
        return Content.objects.filter(status=Content.Status.PENDING)

    if role in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        uni_id = _resolve_university_id(user)
        if not uni_id:
            return Content.objects.none()
        return Content.objects.filter(
            status=Content.Status.PENDING,
            university_id=uni_id,
        )

    return Content.objects.none()


# ============================================================
# Interactions
# ============================================================

def has_liked(content, user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return ContentLike.objects.filter(content=content, user=user).exists()


# ============================================================
# Student Public Rating
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
