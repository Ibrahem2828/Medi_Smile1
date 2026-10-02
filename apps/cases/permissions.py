# apps/cases/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.accounts.models import Role
from medismile.utils.scoping import get_user_university_id, same_university
from .models import Case, CaseSession


# ============================================================
# Helpers
# ============================================================
def is_case_owner(user, case: Case) -> bool:
    return case.patient_id == user.id


def is_case_student(user, case: Case) -> bool:
    return case.student_id == user.id


def is_case_supervisor(user, case: Case) -> bool:
    return case.supervisor_id == user.id


def is_public_case_for_student(user, case: Case) -> bool:
    student_university_id = getattr(getattr(user, "studentprofile_profile", None), "university_id", None)
    return (
        case.is_public
        and case.status == Case.Status.ACCEPTED
        and student_university_id
        and case.university_id == student_university_id
    )


def is_same_university(user, case: Case) -> bool:
    """
    Check if user belongs to the same university as the case.
    ``None`` never matches (an admin without a university must not see
    every unscoped case).
    """
    return same_university(user, case.university_id)


def is_in_user_scope(user, case: Case) -> bool:
    """
    Scope used for staff actions on a case:
    - scoped case: same university as the user;
    - unscoped case (``university`` still NULL, e.g. fresh AI cases): only the
      university the *patient* chose — never "any university".
    """
    user_university_id = get_user_university_id(user)
    if not user_university_id:
        return False
    if case.university_id:
        return case.university_id == user_university_id
    patient_university_id = get_user_university_id(case.patient) if case.patient_id else None
    return patient_university_id == user_university_id


# ============================================================
# Base Permissions
# ============================================================
class IsAuthenticatedActive(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )


# ============================================================
# Case Permissions
# ============================================================
class CanCreateCase(BasePermission):
    """
    - Patient: can create case for himself
    - Non-patient: allowed only via privileged flows (handled in serializer)
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role.name == Role.PATIENT
        )


class CanViewCase(BasePermission):
    """
    Read access rules:
    - Patient: only his own case
    - Student: assigned cases or public accepted cases in their university
    - Supervisor: only supervised cases
    - University Admin: cases of his university
    - IT Support: full read
    """

    def has_object_permission(self, request, view, obj: Case):
        user = request.user

        if user.role.name == Role.TECH_SUPPORT:
            return True

        if user.role.name == Role.PATIENT:
            return is_case_owner(user, obj)

        if user.role.name == Role.STUDENT:
            return is_case_student(user, obj) or is_public_case_for_student(user, obj)

        if user.role.name == Role.SUPERVISOR:
            return is_case_supervisor(user, obj)

        if user.role.name == Role.UNIVERSITY_ADMIN:
            return is_same_university(user, obj)

        return False


class CanUpdateCase(BasePermission):
    """
    Write access rules:
    - Patient: ❌ no updates
    - Student: ❌ no metadata updates
    - Supervisor: limited (status transitions / reviews)
    - University Admin: ❌ no medical changes
    - IT Support: ❌ no medical changes
    """

    def has_object_permission(self, request, view, obj: Case):
        user = request.user

        if obj.status == Case.Status.CLOSED:
            return False

        if user.role.name == Role.SUPERVISOR:
            return is_case_supervisor(user, obj)

        return False


class CanManageCaseStatus(BasePermission):
    """
    State transitions (including NEW/unassigned):
    - Tech Support: any case
    - Supervisor: only his assigned case
    - University Admin: cases in his university
    """

    def has_object_permission(self, request, view, obj: Case):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)

        if role_name == Role.TECH_SUPPORT:
            return True

        if role_name == Role.SUPERVISOR and is_case_supervisor(user, obj):
            return True

        if role_name == Role.UNIVERSITY_ADMIN and is_in_user_scope(user, obj):
            return True

        return False


class CanAssignSupervisor(BasePermission):
    """
    Allow assigning a supervisor to a case and scoping it to that university.
    - Tech Support: any case
    - University Admin: cases in his university or without university
    - Supervisor: can claim if case has no supervisor and (no university or same university)
    """

    def has_object_permission(self, request, view, obj: Case):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)

        if role_name == Role.TECH_SUPPORT:
            return True

        if role_name == Role.UNIVERSITY_ADMIN:
            return is_in_user_scope(user, obj)

        if role_name == Role.SUPERVISOR:
            # supervisor can claim only if unclaimed and within their university scope
            if obj.supervisor_id and obj.supervisor_id != user.id:
                return False
            return is_in_user_scope(user, obj)

        return False


class CanRequestAssignment(BasePermission):
    """
    - Student can request assignment
    - Case must be public and pending assignment
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role.name == Role.STUDENT
        )


# ============================================================
# Session Permissions
# ============================================================
class CanCreateSession(BasePermission):
    """
    - Only assigned student can create session
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role.name == Role.STUDENT
        )


class CanReviewSession(BasePermission):
    """
    - Only assigned supervisor can review session
    """

    def has_object_permission(self, request, view, obj: CaseSession):
        return (
            request.user.is_authenticated
            and request.user.role.name == Role.SUPERVISOR
            and obj.supervisor_id == request.user.id
        )
