# apps/accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """
    Accounts app config.

    - Registers signals (profile auto-creation, role change handling).
    - Keeps app metadata consistent across admin / migrations.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts & Users"

    def ready(self):
        """
        Register signals.

        Important:
        - Keep imports inside ready() to avoid side effects at import time.
        """
        # noqa is intentional to satisfy linters when the module is imported for side effects.
        from . import signals  # noqa: F401
