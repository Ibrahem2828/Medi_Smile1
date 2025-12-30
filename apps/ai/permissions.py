# apps/ai/permissions.py
from rest_framework.permissions import BasePermission
from apps.accounts.models import Role


class CanRequestAIDiagnosis(BasePermission):
    """
    Only PATIENT can request AI diagnosis.
    """

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return getattr(getattr(user, "role", None), "name", None) == Role.PATIENT


class CanAccessAIDiagnosis(BasePermission):
    """
    Object-level access:
    - Patient: own diagnoses
    - Student: diagnoses for cases assigned to them
    - Supervisor: diagnoses for cases supervised by them
    - University Admin: within their university (if case has university)
    - Tech Support: all
    """

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        role = getattr(getattr(user, "role", None), "name", None)

        if role == Role.TECH_SUPPORT:
            return True

        if role == Role.PATIENT:
            return obj.patient_id == user.id

        case = getattr(obj, "case", None)
        if not case:
            return False

        if role == Role.STUDENT:
            return getattr(case, "student_id", None) == user.id

        if role == Role.SUPERVISOR:
            return getattr(case, "supervisor_id", None) == user.id

        if role == Role.UNIVERSITY_ADMIN:
            return getattr(case, "university_id", None) == getattr(user, "university_id", None)

        return False


class CanReviewAIDiagnosis(BasePermission):
    """
    Supervisor-only review action on diagnoses that belong to their cases.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        role = getattr(getattr(user, "role", None), "name", None)
        if role != Role.SUPERVISOR:
            return False

        case = getattr(obj, "case", None)
        if not case:
            return False
        return getattr(case, "supervisor_id", None) == user.id


class CanViewAIHealth(BasePermission):
    """
    Tech Support (or superuser) only: read-only health/config endpoints.
    """

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        role = getattr(getattr(user, "role", None), "name", None)
        return bool(role == Role.TECH_SUPPORT or getattr(user, "is_superuser", False))
