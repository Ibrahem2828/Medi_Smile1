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

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

import apps.messaging.routing


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
        "websocket": AuthMiddlewareStack(
            URLRouter(
                apps.messaging.routing.websocket_urlpatterns
            )
        ),
    }
)
