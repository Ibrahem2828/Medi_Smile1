from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.core.exceptions import ImproperlyConfigured

from .models import Role


# ============================================================
# Helpers
# ============================================================
def get_user_university(user):
    """
    Safely extract user's university from profile.
    Returns None if not applicable.
    """
    if not user or not user.is_authenticated:
        return None

    profile_map = {
        Role.STUDENT: "studentprofile_profile",
        Role.SUPERVISOR: "supervisorprofile_profile",
        Role.UNIVERSITY_ADMIN: "universityadminprofile_profile",
    }

    attr = profile_map.get(user.role.name)
    if not attr:
        return None

    profile = getattr(user, attr, None)
    return getattr(profile, "university", None) if profile else None


def get_object_university(obj):
    """
    Extract university from object.
    Object must expose `university` directly.
    """
    return getattr(obj, "university", None)


# ============================================================
# Base Role Permission
# ============================================================
class BaseRolePermission(BasePermission):
    """
    Base RBAC permission.
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
    High privilege permission.
    Reserved for critical system-level operations.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.role or user.role.name != Role.TECH_SUPPORT:
            return False

        return bool(user.is_staff or user.is_superuser)


# ============================================================
# Ownership Permissions
# ============================================================
class IsOwner(BasePermission):
    """
    Object-level permission.
    Object must have a `user` attribute.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if not hasattr(obj, "user"):
            raise ImproperlyConfigured(
                "IsOwner requires object with `user` attribute."
            )

        return obj.user == user


class IsOwnerOrReadOnly(BasePermission):
    """
    Read-only for everyone with access.
    Write access only for owner.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if not hasattr(obj, "user"):
            raise ImproperlyConfigured(
                "IsOwnerOrReadOnly requires object with `user` attribute."
            )

        return obj.user == user


# ============================================================
# University-scoped Permission
# ============================================================
class IsSameUniversity(BasePermission):
    """
    Object-level permission.
    Allows access only if user and object
    belong to the same university.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        user_university = get_user_university(user)
        if not user_university:
            return False

        obj_university = get_object_university(obj)
        if not obj_university:
            raise ImproperlyConfigured(
                "IsSameUniversity requires object with `university` attribute."
            )

        return user_university == obj_university
