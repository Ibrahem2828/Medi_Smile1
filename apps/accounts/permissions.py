# apps/accounts/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Role


# ============================================================
# Base Role Permission
# ============================================================
class BaseRolePermission(BasePermission):
    """
    Base class for role-based permissions.
    Child classes must define `allowed_roles`.
    """

    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if not user.role:
            return False

        return user.role.name in self.allowed_roles


# ============================================================
# Role-based Permissions
# ============================================================
class IsPatient(BaseRolePermission):
    allowed_roles = (Role.PATIENT,)


class IsStudent(BaseRolePermission):
    allowed_roles = (Role.STUDENT,)


class IsSupervisor(BaseRolePermission):
    allowed_roles = (Role.SUPERVISOR,)


class IsUniversityAdmin(BaseRolePermission):
    allowed_roles = (Role.UNIVERSITY_ADMIN,)


class IsTechSupport(BaseRolePermission):
    allowed_roles = (Role.TECH_SUPPORT,)


# ============================================================
# System / Root-level Permission
# ============================================================
class IsSystemAdmin(BasePermission):
    """
    High-privilege permission.
    Used for critical internal APIs (e.g. create IT Support).
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if not user.role or user.role.name != Role.TECH_SUPPORT:
            return False

        # Extra hardening layer
        return bool(user.is_staff or user.is_superuser)


# ============================================================
# Ownership Permissions
# ============================================================
class IsOwner(BasePermission):
    """
    Allows access only to the owner of the object.
    The object must have a `user` attribute.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        return hasattr(obj, "user") and obj.user == request.user


class IsOwnerOrReadOnly(BasePermission):
    """
    Read-only for everyone with permission,
    write access only for the owner.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        return hasattr(obj, "user") and obj.user == request.user


# ============================================================
# University-scoped Permission
# ============================================================
class IsSameUniversity(BasePermission):
    """
    Allows access only if the requesting user and the object
    belong to the same university.

    Object must have `university` attribute or a related profile with it.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Extract user's university via profile (student / supervisor / admin)
        user_university = None

        for attr in (
            "studentprofile_profile",
            "supervisorprofile_profile",
            "universityadminprofile_profile",
        ):
            profile = getattr(user, attr, None)
            if profile and hasattr(profile, "university"):
                user_university = profile.university
                break

        if not user_university:
            return False

        # Check object's university
        obj_university = getattr(obj, "university", None)
        return obj_university == user_university
