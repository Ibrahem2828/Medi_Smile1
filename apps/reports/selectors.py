# apps/reports/selectors.py
from django.db.models import Q
from apps.accounts.models import Role
from .models import Report


def get_user_university_ids(user) -> set:
    """
    Collect university IDs linked to the user.
    Supports FK and future M2M extension.
    """
    ids = set()

    if hasattr(user, "university_id") and user.university_id:
        ids.add(user.university_id)

    if hasattr(user, "universities"):
        ids |= set(user.universities.values_list("id", flat=True))

    return ids


def reports_queryset_for_user(user):
    """
    Base scoped queryset for reports visibility.
    """

    qs = (
        Report.objects
        .select_related("student", "university", "generated_by")
        .order_by("-generated_at")
    )

    if not user or not getattr(user, "role", None):
        return Report.objects.none()

    role_name = user.role.name

    # Tech Support → all reports
    if role_name == Role.TECH_SUPPORT:
        return qs

    # University Admin → reports of own university
    if role_name == Role.UNIVERSITY_ADMIN:
        return qs.filter(university_id__in=get_user_university_ids(user))

    # Supervisor → reports of same university
    if role_name == Role.SUPERVISOR:
        if hasattr(user, "supervisorprofile"):
            return qs.filter(university=user.supervisorprofile.university)
        return Report.objects.none()

    # Student → own reports only (active)
    if role_name == Role.STUDENT:
        return qs.filter(student=user, is_active=True)

    return Report.objects.none()


def reports_for_student(student, viewer):
    """
    Reports for a specific student with viewer scoping.
    """
    qs = reports_queryset_for_user(viewer)

    if viewer.role.name == Role.STUDENT and viewer.id != student.id:
        return Report.objects.none()

    return qs.filter(student=student)


def reports_for_university(university, viewer):
    """
    Reports for a specific university with viewer scoping.
    """
    qs = reports_queryset_for_user(viewer)

    return qs.filter(university=university)
