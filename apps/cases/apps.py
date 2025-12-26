# apps/cases/apps.py
from django.apps import AppConfig


class CasesConfig(AppConfig):
    """
    Cases app configuration.

    - Core medical workflow (Cases, Sessions, Assignments).
    - Integrates with Universities for scoping.
    - Integrates with Accounts for role-based access.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cases"
    verbose_name = "Medical Cases"

    def ready(self):
        """
        Hook for future signals:
        - Case creation audit
        - Automatic notifications
        - Status transition logging
        """
        # from . import signals  # noqa: F401
        pass
