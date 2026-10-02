"""
ASGI config for medismile project.

This module exposes the ASGI callable as a module-level variable named `application`.

It supports:
- HTTP via Django ASGI application
- WebSocket via Django Channels

Docs:
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application


# ============================================================
# Django settings
# ============================================================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medismile.settings")


# ============================================================
# Initialize Django ASGI application
# ------------------------------------------------------------
# This must be done BEFORE importing ORM-dependent modules
# ============================================================
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from channels.routing import ProtocolTypeRouter, URLRouter

import apps.messaging.routing
from medismile.ws_auth import JWTAuthMiddleware


# ============================================================
# ASGI application
# ============================================================
application = ProtocolTypeRouter(
    {
        # -------------------------
        # HTTP requests
        # -------------------------
        "http": django_asgi_app,

        # -------------------------
        # WebSocket connections
        # -------------------------
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                JWTAuthMiddleware(
                    URLRouter(apps.messaging.routing.websocket_urlpatterns)
                )
            )
        ),
    }
)
