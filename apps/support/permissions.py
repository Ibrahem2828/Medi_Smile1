# apps/support/permissions.py
from rest_framework.permissions import BasePermission
from apps.accounts.models import Role


def _same_university_scope(user_a, user_b) -> bool:
    """
    Compare university scope via profiles or M2M.
    """
    profile_attrs = (
        "studentprofile_profile",
        "supervisorprofile_profile",
        "universityadminprofile_profile",
    )

    uni_a = set()
    uni_b = set()
    for attr in profile_attrs:
        pa = getattr(user_a, attr, None)
        pb = getattr(user_b, attr, None)
        if pa and getattr(pa, "university_id", None):
            uni_a.add(pa.university_id)
        if pb and getattr(pb, "university_id", None):
            uni_b.add(pb.university_id)

    if hasattr(user_a, "universities"):
        uni_a |= set(user_a.universities.values_list("id", flat=True))
    if hasattr(user_b, "universities"):
        uni_b |= set(user_b.universities.values_list("id", flat=True))

    return bool(uni_a and uni_b and uni_a.intersection(uni_b))


class IsTechSupport(BasePermission):
    """
    Allows access only to technical support users.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role
            and request.user.role.name == Role.TECH_SUPPORT
        )


class IsTicketOwner(BasePermission):
    """
    Allows access only to the ticket owner.
    """

    def has_object_permission(self, request, view, obj):
        return obj.created_by_id == request.user.id


class IsUniversityAdminInScope(BasePermission):
    """
    University admin can access tickets created by users
    belonging to the same university scope.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.role or user.role.name != Role.UNIVERSITY_ADMIN:
            return False

        return _same_university_scope(user, obj.created_by)


class IsOwnerOrUniversityAdminOrTech(BasePermission):
    """
    Composite permission:
    - Ticket owner
    - University admin (same scope)
    - Tech support
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)

        if role_name == Role.TECH_SUPPORT:
            return True

        if obj.created_by_id == user.id:
            return True

        if role_name == Role.UNIVERSITY_ADMIN:
            return _same_university_scope(user, obj.created_by)

        return False
