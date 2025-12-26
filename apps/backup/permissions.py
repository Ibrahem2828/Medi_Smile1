from rest_framework.permissions import BasePermission
from apps.accounts.models import Role


class IsTechSupport(BasePermission):
    """
    Backup operations are restricted to Tech Support only.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request.user.role, "name", None) == Role.TECH_SUPPORT
        )
