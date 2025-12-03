from __future__ import annotations

from typing import Optional, Tuple

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from django.conf import settings

from apps.accounts.models import User


def resolve_request_user(request, *, allow_body: bool = True, allow_query: bool = True) -> Optional[User]:
    """
    Return the authenticated user if available; otherwise try to resolve a user
    from `user_id` passed in the body or query params. This lets endpoints keep
    working while global authentication is disabled.
    """
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user

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
    Ensure we return a valid user or an error Response explaining what is missing.
    """
    user = resolve_request_user(request, allow_query=allow_query)
    if user:
        return user, None

    user_id = None
    if hasattr(request, "data"):
        user_id = request.data.get(error_key)
    if not user_id and allow_query and hasattr(request, "query_params"):
        user_id = request.query_params.get(error_key)

    if not user_id:
        return None, Response({
            'error': _(f'{error_key} is required when authentication is disabled')
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        return User.objects.get(id=user_id), None
    except User.DoesNotExist:
        return None, Response({
            'error': _('User not found')
        }, status=status.HTTP_404_NOT_FOUND)


def business_rules_disabled() -> bool:
    """Central flag to suspend role/ownership checks when debugging."""
    return getattr(settings, 'DISABLE_BUSINESS_RULES', False)

