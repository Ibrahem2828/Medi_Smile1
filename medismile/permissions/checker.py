from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .matrix import get_policy


@dataclass
class PermissionDecision:
    allowed: bool
    reason: str | None = None


OwnershipChecker = Callable[[object, object], bool]
ScopeChecker = Callable[[object, object], bool]
StateChecker = Callable[[object], bool]


def has_access(
    *,
    user,
    resource: str,
    action: str,
    obj=None,
    ownership_checker: Optional[OwnershipChecker] = None,
    scope_checker: Optional[ScopeChecker] = None,
    state_checker: Optional[StateChecker] = None,
) -> PermissionDecision:
    """
    Central permission evaluator:
    Authentication → Role → Ownership → Scope → State.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return PermissionDecision(False, "auth_required")

    if not getattr(user, "is_active", False):
        return PermissionDecision(False, "user_inactive")

    role_name = getattr(user, "role_name", None) or getattr(
        getattr(user, "role", None), "name", None
    )
    if not role_name:
        return PermissionDecision(False, "role_missing")

    policy = get_policy(resource, action)
    if not policy:
        return PermissionDecision(False, "policy_missing")

    if role_name not in policy.get("roles", set()):
        return PermissionDecision(False, "role_forbidden")

    # Ownership
    if policy.get("ownership_required") and ownership_checker and obj is not None:
        if not ownership_checker(user, obj):
            return PermissionDecision(False, "ownership_failed")

    # University scope
    if policy.get("university_scope_required") and scope_checker and obj is not None:
        if not scope_checker(user, obj):
            return PermissionDecision(False, "scope_failed")

    # State check
    if policy.get("state_required") and state_checker:
        if not state_checker(obj):
            return PermissionDecision(False, "state_failed")

    return PermissionDecision(True)
