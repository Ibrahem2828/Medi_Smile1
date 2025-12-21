from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts & Users"

    def ready(self):
        """
        Ensure signals are registered when the app is ready.
        This is critical for RBAC + profile auto-creation.
        """
        import apps.accounts.signals  # noqa
