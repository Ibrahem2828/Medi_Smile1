# apps/evaluations/permissions.py
from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


def _get_user_university_ids(user) -> set:
    ids = set()
    if not user:
        return ids

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
            ids.add(uni_id)

    rel = getattr(user, "universities", None)
    if rel is not None and hasattr(rel, "all"):
        ids |= set(rel.values_list("id", flat=True))
    return ids


class CanViewEvaluation(BasePermission):
    """
    - Patient: view own evaluations only
    - Student: view evaluations they created or that target them
    - Supervisor / University Admin: view evaluations within their university scope
    - Tech Support: denied
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)

        if role_name == Role.PATIENT:
            return obj.evaluator_id == user.id

        if role_name == Role.STUDENT:
            return obj.evaluator_id == user.id or obj.student_id == user.id

        if role_name in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
            return obj.university_id in _get_user_university_ids(user)

        return False


class CanCreateEvaluation(BasePermission):
    def has_permission(self, request, view):
        role_name = getattr(getattr(request.user, "role", None), "name", None)
        return role_name in {
            Role.PATIENT,
            Role.STUDENT,
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
        }


class CanAdjustEvaluation(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)
        if obj.is_locked:
            return False
        if role_name not in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
            return False
        return obj.university_id in _get_user_university_ids(user)


class CanFinalizeEvaluation(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)
        if obj.is_locked:
            return False
        if role_name != Role.UNIVERSITY_ADMIN:
            return False
        return obj.university_id in _get_user_university_ids(user)
