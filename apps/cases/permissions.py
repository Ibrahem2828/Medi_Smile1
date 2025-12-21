from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.utils.translation import gettext_lazy as _

from medismile.utils.auth import resolve_request_user
from .models import Case, CaseSession


# ============================================================
# Base Permission (Shared Logic)
# ============================================================

class BaseCasePermission(BasePermission):
    """
    Base permission class for all Case & Session permissions.

    - Supports JWT-authenticated users
    - Supports fallback user resolution when needed
    """

    message = _("You do not have permission to perform this action.")

    def get_user(self, request):
        """
        Resolve user from request (JWT or fallback user_id).
        """
        return resolve_request_user(request)


# ============================================================
# Case-Level Permissions
# ============================================================

class IsCasePatient(BaseCasePermission):
    """
    Allow access ONLY to the patient who owns the case.
    """

    def has_object_permission(self, request, view, obj: Case):
        user = self.get_user(request)
        return (
            user is not None
            and user.role == "patient"
            and obj.patient_id == user.id
        )


class IsCaseStudent(BaseCasePermission):
    """
    Allow access ONLY to the student assigned to the case.
    """

    def has_object_permission(self, request, view, obj: Case):
        user = self.get_user(request)
        return (
            user is not None
            and user.role == "student"
            and obj.student_id == user.id
        )


class IsCaseSupervisor(BaseCasePermission):
    """
    Allow access ONLY to the supervisor assigned to the case.
    """

    def has_object_permission(self, request, view, obj: Case):
        user = self.get_user(request)
        return (
            user is not None
            and user.role == "supervisor"
            and obj.supervisor_id == user.id
        )


class IsCaseOwnerOrSupervisor(BaseCasePermission):
    """
    Allow access to:
    - Case patient (read-only)
    - Assigned student (full case workflow)
    - Assigned supervisor (review & approval)
    """

    def has_object_permission(self, request, view, obj: Case):
        user = self.get_user(request)
        if not user:
            return False

        if user.role == "patient" and obj.patient_id == user.id:
            return True

        if user.role == "student" and obj.student_id == user.id:
            return True

        if user.role == "supervisor" and obj.supervisor_id == user.id:
            return True

        return False


# ============================================================
# Case Session Permissions
# ============================================================

class IsSessionStudent(BaseCasePermission):
    """
    Allow ONLY the student who created the session.
    """

    def has_object_permission(self, request, view, obj: CaseSession):
        user = self.get_user(request)
        return (
            user is not None
            and user.role == "student"
            and obj.student_id == user.id
        )


class IsSessionSupervisor(BaseCasePermission):
    """
    Allow ONLY the supervisor assigned to review the session.
    """

    def has_object_permission(self, request, view, obj: CaseSession):
        user = self.get_user(request)
        return (
            user is not None
            and user.role == "supervisor"
            and obj.supervisor_id == user.id
        )


class IsSessionPatientReadOnly(BaseCasePermission):
    """
    Allow patient to READ ONLY sessions related to their own case.
    """

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj: CaseSession):
        user = self.get_user(request)
        return (
            user is not None
            and user.role == "patient"
            and obj.case.patient_id == user.id
        )


# ============================================================
# Administrative / System Roles
# ============================================================

class IsUniversityAdmin(BaseCasePermission):
    """
    University admin:
    - Read-only access to ALL cases within their university
    - No ability to modify medical data
    """

    def has_permission(self, request, view):
        user = self.get_user(request)
        return user is not None and user.role == "university_admin"


class IsTechSupport(BaseCasePermission):
    """
    IT Support:
    - Platform-level read-only access
    - Used ONLY for auditing, debugging, and emergency support
    """

    def has_permission(self, request, view):
        user = self.get_user(request)
        return user is not None and user.role == "tech_support"
