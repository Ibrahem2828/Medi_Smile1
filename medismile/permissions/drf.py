from __future__ import annotations

from typing import Callable, Optional
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

from .checker import has_access


class MatrixPermission(BasePermission):
    """
    DRF permission class powered by the central matrix.

    Expected view attributes:
    - permission_resource: str (e.g., "messaging.room")
    - permission_action: str (optional; defaults based on method)
    - permission_ownership_checker: callable(user, obj) -> bool (optional)
    - permission_scope_checker: callable(user, obj) -> bool (optional)
    - permission_state_checker: callable(obj) -> bool (optional)
    - permission_object: optional object for has_permission; otherwise object perms use get_object().
    """

    def _resolve_action(self, request, view) -> str:
        if getattr(view, "permission_action", None):
            return view.permission_action

        if request.method == "GET":
            return "view"
        if request.method == "POST":
            return "create"
        if request.method in {"PUT", "PATCH"}:
            return "update"
        if request.method == "DELETE":
            return "delete"
        return "view"

    def has_permission(self, request, view):
        resource = getattr(view, "permission_resource", None)
        if not resource:
            return False

        action = self._resolve_action(request, view)

        obj = getattr(view, "permission_object", None)
        decision = has_access(
            user=request.user,
            resource=resource,
            action=action,
            obj=obj,
            ownership_checker=getattr(view, "permission_ownership_checker", None),
            scope_checker=getattr(view, "permission_scope_checker", None),
            state_checker=getattr(view, "permission_state_checker", None),
        )

        if not decision.allowed:
            self.message = f"permission_denied:{decision.reason}"
        return decision.allowed

    def has_object_permission(self, request, view, obj):
        resource = getattr(view, "permission_resource", None)
        if not resource:
            return False

        action = self._resolve_action(request, view)
        decision = has_access(
            user=request.user,
            resource=resource,
            action=action,
            obj=obj,
            ownership_checker=getattr(view, "permission_ownership_checker", None),
            scope_checker=getattr(view, "permission_scope_checker", None),
            state_checker=getattr(view, "permission_state_checker", None),
        )
        if not decision.allowed:
            self.message = f"permission_denied:{decision.reason}"
        return decision.allowed
