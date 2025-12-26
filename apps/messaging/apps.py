# apps/messaging/apps.py
from django.apps import AppConfig


class MessagingConfig(AppConfig):
    """
    Messaging application configuration.

    Responsibilities:
    - Case-scoped messaging
    - REST + WebSocket integration
    - Notifications triggers
    - Audit hooks

    No business logic should live here.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.messaging"
    verbose_name = "Messaging"

    def ready(self):
        """
        Load signals for messaging lifecycle.
        """
        from . import signals  # noqa: F401
