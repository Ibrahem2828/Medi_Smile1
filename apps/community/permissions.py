# apps/community/permissions.py
from rest_framework.permissions import BasePermission
from apps.accounts.models import Role
from .selectors import _resolve_university_id


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

        if getattr(obj, "is_deleted", False):
            return False

        if obj.status != obj.Status.APPROVED:
            return False

        if role == Role.PATIENT:
            return obj.university_id == _resolve_university_id(user)

        if role in {
            Role.STUDENT,
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
        }:
            return obj.university_id == _resolve_university_id(user)

        return False


class CanModerateContent(BasePermission):
    """
    Approve / Reject:
    - Supervisor (same university)
    """

    def has_object_permission(self, request, view, obj):
        role = getattr(getattr(request.user, "role", None), "name", None)

        if role == Role.SUPERVISOR:
            return obj.university_id == _resolve_university_id(request.user)

        return False


class CanLikeContent(BasePermission):
    """
    - All authenticated users
    - Patient: like only (no comment)
    """

    def has_permission(self, request, view):
        role = getattr(getattr(request.user, "role", None), "name", None)
        return request.user.is_authenticated and role != Role.TECH_SUPPORT


class CanCommentContent(BasePermission):
    """
    - Student / Supervisor
    - Patient: NOT allowed
    """

    def has_permission(self, request, view):
        role = getattr(getattr(request.user, "role", None), "name", None)
        return role in {
            Role.STUDENT,
            Role.SUPERVISOR,
        }


class CanViewApprovalLogs(BasePermission):
    """
    - University Admin / Tech Support
    """

    def has_permission(self, request, view):
        role = getattr(getattr(request.user, "role", None), "name", None)
        return role in {
            Role.UNIVERSITY_ADMIN,
            Role.TECH_SUPPORT,
        }
