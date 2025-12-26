# apps/reports/permissions.py
from rest_framework.permissions import BasePermission
from apps.accounts.models import Role


class CanViewReport(BasePermission):
    """
    Permission to VIEW a report.

    Rules:
    - Student: can view own reports only
    - Supervisor: reports of students in same university
    - University Admin: reports of own university
    - Tech Support: all reports
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        role_name = getattr(getattr(user, "role", None), "name", None)

        if role_name == Role.TECH_SUPPORT:
            return True

        if role_name == Role.UNIVERSITY_ADMIN:
            return obj.university_id == getattr(user, "university_id", None)

        if role_name == Role.SUPERVISOR:
            # supervisor may belong to more than one university in future
            if hasattr(user, "supervisorprofile"):
                return obj.university_id == user.supervisorprofile.university_id

        if role_name == Role.STUDENT:
            return obj.student_id == user.id

        return False


class CanGenerateReport(BasePermission):
    """
    Permission to GENERATE reports.

    Allowed:
    - Supervisor
    - University Admin
    - Tech Support
    """

    def has_permission(self, request, view):
        role_name = getattr(getattr(request.user, "role", None), "name", None)
        return role_name in {
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
            Role.TECH_SUPPORT,
        }


class CanToggleReportVisibility(BasePermission):
    """
    Permission to toggle report visibility (is_active).

    Allowed:
    - University Admin
    - Tech Support
    """

    def has_object_permission(self, request, view, obj):
        role_name = getattr(getattr(request.user, "role", None), "name", None)

        if role_name == Role.TECH_SUPPORT:
            return True

        if role_name == Role.UNIVERSITY_ADMIN:
            return obj.university_id == getattr(request.user, "university_id", None)

        return False
