# apps/support/permissions.py
from rest_framework.permissions import BasePermission
from apps.accounts.models import Role


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

        # SupportTicket has no direct university field
        ticket_owner = obj.created_by

        # Case 1: FK university
        if hasattr(ticket_owner, "university_id") and hasattr(user, "university_id"):
            return ticket_owner.university_id == user.university_id

        # Case 2: M2M universities
        if hasattr(ticket_owner, "universities") and hasattr(user, "universities"):
            return ticket_owner.universities.filter(
                id__in=user.universities.values_list("id", flat=True)
            ).exists()

        return False


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
            ticket_owner = obj.created_by

            if hasattr(ticket_owner, "university_id") and hasattr(user, "university_id"):
                return ticket_owner.university_id == user.university_id

            if hasattr(ticket_owner, "universities") and hasattr(user, "universities"):
                return ticket_owner.universities.filter(
                    id__in=user.universities.values_list("id", flat=True)
                ).exists()

        return False
