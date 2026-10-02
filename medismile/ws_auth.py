"""JWT authentication for Channels WebSocket connections."""
from __future__ import annotations

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def _jwt_user(raw_token: str):
    try:
        authentication = JWTAuthentication()
        token = authentication.get_validated_token(raw_token)
        user = authentication.get_user(token)
        return user if user.is_active else AnonymousUser()
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Authenticate a Bearer token from the WebSocket handshake header.

    Query-string tokens are intentionally not accepted because they leak into
    access logs. Session auth remains available for the Django admin.
    """

    async def __call__(self, scope, receive, send):
        user = scope.get("user")
        if not getattr(user, "is_authenticated", False):
            headers = dict(scope.get("headers") or [])
            authorization = headers.get(b"authorization", b"").decode("latin1")
            scheme, _, raw_token = authorization.partition(" ")
            if scheme.lower() == "bearer" and raw_token:
                scope = dict(scope)
                scope["user"] = await _jwt_user(raw_token.strip())
        return await super().__call__(scope, receive, send)
