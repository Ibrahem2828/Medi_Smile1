# apps/community/permissions.py
from rest_framework.permissions import BasePermission
from apps.accounts.models import Role


class CanCreateContent(BasePermission):
    """
    - Student / Supervisor / University Admin / Tech Support
    - Patient: NOT allowed
    """

    def has_permission(self, request, view):
        role = getattr(getattr(request.user, "role", None), "name", None)
        return role in {
            Role.STUDENT,
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
            Role.TECH_SUPPORT,
        }


class CanViewContent(BasePermission):
    """
    - Approved content:
        - Public → everyone
        - Private → same university
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = getattr(getattr(user, "role", None), "name", None)

        if obj.status != obj.Status.APPROVED:
            return False

        if obj.is_public:
            return True

        if role in {
            Role.STUDENT,
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
        }:
            return obj.university_id == getattr(user, "university_id", None)

        return False


class CanModerateContent(BasePermission):
    """
    Approve / Reject:
    - Supervisor (same university)
    - University Admin (same university)
    - Tech Support (all)
    """

    def has_object_permission(self, request, view, obj):
        role = getattr(getattr(request.user, "role", None), "name", None)

        if role == Role.TECH_SUPPORT:
            return True

        if role in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
            return obj.university_id == getattr(request.user, "university_id", None)

        return False


class CanLikeContent(BasePermission):
    """
    - All authenticated users
    - Patient: like only (no comment)
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated


class CanCommentContent(BasePermission):
    """
    - Student / Supervisor / University Admin
    - Patient: NOT allowed
    """

    def has_permission(self, request, view):
        role = getattr(getattr(request.user, "role", None), "name", None)
        return role in {
            Role.STUDENT,
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
        }
