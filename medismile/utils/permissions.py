from rest_framework import permissions


class RoleBasedPermission(permissions.BasePermission):
    """
    Custom permission to only allow users with specific roles.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        required_roles = getattr(view, 'required_roles', [])
        
        if not required_roles:
            return True
            
        return request.user.role in required_roles