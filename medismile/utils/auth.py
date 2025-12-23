from __future__ import annotations

from typing import Optional, Tuple

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response

from apps.accounts.models import User


# ============================================================
# User Resolution Utilities
# ============================================================

def resolve_request_user(
    request,
    *,
    allow_body: bool = True,
    allow_query: bool = True,
) -> Optional[User]:
    """
    Resolve the current user associated with the request.

    Priority:
    1. Authenticated request.user (JWT / Session)
    2. Explicit user_id from request body (ONLY if explicitly allowed)
    3. Explicit user_id from query params (ONLY if explicitly allowed)

    ⚠️ SECURITY NOTE:
    - Fallback to user_id MUST be used only for:
        - internal services
        - debugging
        - trusted system-to-system calls
    - NEVER rely on this in public endpoints without permissions.
    """

    # --------------------------------------------------------
    # 1. Authenticated user (primary & secure path)
    # --------------------------------------------------------
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user

    # --------------------------------------------------------
    # 2. Fallback resolution (controlled & optional)
    # --------------------------------------------------------
    if not business_rules_disabled():
        return None

    user_id = None

    if allow_body and hasattr(request, "data"):
        user_id = request.data.get("user_id")

    if not user_id and allow_query and hasattr(request, "query_params"):
        user_id = request.query_params.get("user_id")

    if not user_id:
        return None

    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def require_request_user(
    request,
    *,
    allow_query: bool = True,
    error_key: str = "user_id",
) -> Tuple[Optional[User], Optional[Response]]:
    """
    Ensure a valid user is resolved, otherwise return a structured error response.

    This helper is useful for:
    - internal APIs
    - admin tools
    - background jobs
    """

    user = resolve_request_user(request, allow_query=allow_query)
    if user:
        return user, None

    # --------------------------------------------------------
    # Build proper error response
    # --------------------------------------------------------
    user_id = None

    if hasattr(request, "data"):
        user_id = request.data.get(error_key)

    if not user_id and allow_query and hasattr(request, "query_params"):
        user_id = request.query_params.get(error_key)

    if not user_id:
        return None, Response(
            {
                "error": _(f"{error_key} is required when authentication is disabled"),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        return User.objects.get(id=user_id), None
    except User.DoesNotExist:
        return None, Response(
            {
                "error": _("User not found"),
            },
            status=status.HTTP_404_NOT_FOUND,
        )


# ============================================================
# Feature Flags / Debug Controls
# ============================================================

def business_rules_disabled() -> bool:
    """
    Centralized flag to disable role / ownership / auth rules.

    ⚠️ MUST be False in production.
    Intended usage:
    - Local development
    - Internal admin tools
    - Controlled test environments
    """
    return bool(getattr(settings, "DISABLE_BUSINESS_RULES", False))
