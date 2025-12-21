from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class RoleBasedPermission(permissions.BasePermission):
    """
    System-level Role-Based Access Control (RBAC).

    Usage (in views):
    -----------------
    class ExampleView(APIView):
        permission_classes = [RoleBasedPermission]
        required_roles = ["university_admin", "tech_support"]

    Behavior:
    ---------
    - If user is not authenticated → deny
    - If no required_roles defined → allow
    - If user role is in required_roles → allow
    """

    message = "ليس لديك الصلاحية للوصول إلى هذا المورد."

    def has_permission(self, request, view):
        # --------------------------------------------------
        # Authentication check
        # --------------------------------------------------
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        # --------------------------------------------------
        # Fetch required roles from the view
        # --------------------------------------------------
        required_roles = getattr(view, "required_roles", None)

        # If no roles defined → open to authenticated users
        if not required_roles:
            return True

        # --------------------------------------------------
        # Normalize roles
        # --------------------------------------------------
        if isinstance(required_roles, str):
            required_roles = [required_roles]

        # --------------------------------------------------
        # User role resolution
        # --------------------------------------------------
        user_role = user.role

        # Safety check
        if not user_role:
            return False

        # --------------------------------------------------
        # Final decision
        # --------------------------------------------------
        return user_role in required_roles


class AllowAnyAuthenticated(permissions.BasePermission):
    """
    Explicit permission class to allow any authenticated user.
    Useful for readability and documentation.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
        )


class IsSystemAdmin(permissions.BasePermission):
    """
    Allow only system-level administrators (Tech Support).
    """

    message = "هذه العملية مسموحة لمسؤولي النظام فقط."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "tech_support"
        )
