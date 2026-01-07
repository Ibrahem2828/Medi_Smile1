# apps/reports/selectors.py
from apps.accounts.models import Role
from apps.cases.models import Case

from .models import Report


def _resolve_university_id(user):
    if not user:
        return None

    for attr in (
        "studentprofile_profile",
        "supervisorprofile_profile",
        "universityadminprofile_profile",
        "patientprofile_profile",
    ):
        profile = getattr(user, attr, None)
        uni_id = getattr(profile, "university_id", None)
        if uni_id:
            return uni_id
    return None


def get_user_university_ids(user) -> set:
    uni_id = _resolve_university_id(user)
    return {uni_id} if uni_id else set()


def reports_queryset_for_user(user):
    qs = (
        Report.objects
        .select_related("author", "student", "supervisor", "university", "generated_by", "approved_by")
        .order_by("-created_at")
    )

    if not user or not getattr(user, "role", None):
        return Report.objects.none()

    role_name = user.role.name

    if role_name == Role.UNIVERSITY_ADMIN:
        return qs.filter(university_id__in=get_user_university_ids(user))

    if role_name == Role.SUPERVISOR:
        return qs.filter(university_id__in=get_user_university_ids(user))

    if role_name == Role.STUDENT:
        return qs.filter(author=user)

    if role_name == Role.PATIENT:
        case_ids = Case.objects.filter(patient=user).values_list("id", flat=True)
        return qs.filter(
            target_type=Report.TargetType.CASE,
            target_id__in=case_ids,
            status__in={Report.Status.APPROVED, Report.Status.LOCKED},
            is_active=True,
        )

    return qs.none()


def reports_for_student(student, viewer):
    qs = reports_queryset_for_user(viewer)
    if viewer.role.name == Role.STUDENT and viewer.id != student.id:
        return Report.objects.none()
    return qs.filter(student=student)


def reports_for_university(university, viewer):
    qs = reports_queryset_for_user(viewer)
    return qs.filter(university=university)
