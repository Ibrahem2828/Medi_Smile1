# apps/accounts/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Role


# ============================================================
# Base Helpers
# ============================================================
def is_self(request, obj):
    """
    Check if the current user is accessing his own object.
    """
    if hasattr(obj, "user"):
        return obj.user_id == request.user.id
    return obj.id == request.user.id


# ============================================================
# Generic Role-Based Permissions
# ============================================================
class IsAuthenticatedAndActive(BasePermission):
    """
    Base permission:
    - User must be authenticated
    - User must be active
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )


class IsTechSupport(BasePermission):
    """
    Allow access only for Tech Support role.
    """

    def has_permission(self, request, view):
        role_name = getattr(getattr(request, "user", None), "role", None)
        return bool(getattr(request.user, "is_authenticated", False) and getattr(role_name, "name", None) == Role.TECH_SUPPORT)


class IsUniversityAdmin(BasePermission):
    """
    Allow access only for University Admin role.
    """

    def has_permission(self, request, view):
        role_name = getattr(getattr(request, "user", None), "role", None)
        return bool(getattr(request.user, "is_authenticated", False) and getattr(role_name, "name", None) == Role.UNIVERSITY_ADMIN)


class IsSupervisor(BasePermission):
    def has_permission(self, request, view):
        role_name = getattr(getattr(request, "user", None), "role", None)
        return bool(getattr(request.user, "is_authenticated", False) and getattr(role_name, "name", None) == Role.SUPERVISOR)


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        role_name = getattr(getattr(request, "user", None), "role", None)
        return bool(getattr(request.user, "is_authenticated", False) and getattr(role_name, "name", None) == Role.STUDENT)


class IsPatient(BasePermission):
    def has_permission(self, request, view):
        role_name = getattr(getattr(request, "user", None), "role", None)
        return bool(getattr(request.user, "is_authenticated", False) and getattr(role_name, "name", None) == Role.PATIENT)


# ============================================================
# Object-Level Permissions
# ============================================================
class IsSelfOrReadOnly(BasePermission):
    """
    Object-level permission:
    - SAFE_METHODS: allowed
    - WRITE: only if object belongs to the same user
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return is_self(request, obj)


class IsSelfOnly(BasePermission):
    """
    Object-level permission:
    - Access only allowed to owner (self)
    """

    def has_object_permission(self, request, view, obj):
        return is_self(request, obj)


# ============================================================
# Account Creation Permissions
# ============================================================
class CanCreatePatient(BasePermission):
    """
    Patient:
    - Can self-register
    """

    def has_permission(self, request, view):
        return True


class CanCreateStudent(BasePermission):
    """
    Student:
    - Only University Admin can create
    """

    def has_permission(self, request, view):
        role_name = getattr(getattr(request, "user", None), "role", None)
        return bool(getattr(request.user, "is_authenticated", False) and getattr(role_name, "name", None) == Role.UNIVERSITY_ADMIN)


class CanCreateSupervisor(BasePermission):
    """
    Supervisor:
    - Only University Admin can create
    """

    def has_permission(self, request, view):
        role_name = getattr(getattr(request, "user", None), "role", None)
        return bool(getattr(request.user, "is_authenticated", False) and getattr(role_name, "name", None) == Role.UNIVERSITY_ADMIN)


class CanCreateUniversityAdmin(BasePermission):
    """
    University Admin:
    - Only Tech Support can create
    """

    def has_permission(self, request, view):
        role_name = getattr(getattr(request, "user", None), "role", None)
        return bool(getattr(request.user, "is_authenticated", False) and getattr(role_name, "name", None) == Role.TECH_SUPPORT)


class CanCreateTechSupport(BasePermission):
    """
    Tech Support:
    - Only system-level superuser / Tech Support
    """

    def has_permission(self, request, view):
        role_name = getattr(getattr(request, "user", None), "role", None)
        return bool(
            getattr(request.user, "is_authenticated", False)
            and (
                getattr(request.user, "is_superuser", False)
                or getattr(role_name, "name", None) == Role.TECH_SUPPORT
            )
        )
