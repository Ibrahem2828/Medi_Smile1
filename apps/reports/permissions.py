# apps/reports/permissions.py
from rest_framework.permissions import BasePermission

from apps.accounts.models import Role
from apps.cases.models import Case
from .selectors import _resolve_university_id


class CanViewReport(BasePermission):
    """
    View rules:
    - Student: own reports
    - Supervisor: same university
    - University Admin: same university
    - Patient: approved/locked case reports for their own cases
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)

        if role_name == Role.UNIVERSITY_ADMIN:
            return obj.university_id == _resolve_university_id(user)

        if role_name == Role.SUPERVISOR:
            return obj.university_id == _resolve_university_id(user)

        if role_name == Role.STUDENT:
            return obj.author_id == user.id

        if role_name == Role.PATIENT:
            if obj.status not in {obj.Status.APPROVED, obj.Status.LOCKED}:
                return False
            if obj.target_type != obj.TargetType.CASE:
                return False
            return Case.objects.filter(id=obj.target_id, patient=user).exists()

        return False


class CanCreateReport(BasePermission):
    def has_permission(self, request, view):
        role_name = getattr(getattr(request.user, "role", None), "name", None)
        return role_name in {Role.STUDENT, Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}


class CanApproveReport(BasePermission):
    def has_permission(self, request, view):
        role_name = getattr(getattr(request.user, "role", None), "name", None)
        return role_name == Role.SUPERVISOR


class CanExportReport(BasePermission):
    def has_permission(self, request, view):
        role_name = getattr(getattr(request.user, "role", None), "name", None)
        return role_name == Role.UNIVERSITY_ADMIN
