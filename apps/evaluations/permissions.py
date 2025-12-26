# apps/evaluations/permissions.py
from rest_framework.permissions import BasePermission
from apps.accounts.models import Role


class CanViewEvaluation(BasePermission):
    """
    - Student: view own evaluations only
    - Supervisor / University Admin: view evaluations within their university scope
    - Tech Support: optional (by default NO medical/academic content) -> deny
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)

        if role_name == Role.STUDENT:
            return obj.student_id == user.id

        if role_name in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
            # evaluation has university FK
            return obj.university_id in _get_user_university_ids(user)

        # Tech support should not access academic evaluations by default
        return False


class CanCreateEvaluation(BasePermission):
    """
    Only:
    - Supervisor
    - University Admin
    """

    def has_permission(self, request, view):
        role_name = getattr(getattr(request.user, "role", None), "name", None)
        return role_name in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}


class CanUpdateEvaluation(BasePermission):
    """
    Update only allowed for evaluator (or university admin in same scope),
    and not allowed if FINAL.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)

        if obj.is_locked:
            return False

        if role_name == Role.SUPERVISOR:
            return obj.evaluator_id == user.id

        if role_name == Role.UNIVERSITY_ADMIN:
            return obj.university_id in _get_user_university_ids(user)

        return False


class CanChangeEvaluationStatus(BasePermission):
    """
    submit/finalize:
    - evaluator supervisor
    - university admin in scope
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)

        if obj.is_locked:
            return False

        if role_name == Role.SUPERVISOR:
            return obj.evaluator_id == user.id

        if role_name == Role.UNIVERSITY_ADMIN:
            return obj.university_id in _get_user_university_ids(user)

        return False


def _get_user_university_ids(user) -> set:
    ids = set()
    if getattr(user, "university_id", None):
        ids.add(user.university_id)
    rel = getattr(user, "universities", None)
    if rel is not None and hasattr(rel, "all"):
        ids |= set(rel.values_list("id", flat=True))
    return ids
