from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cases"
    verbose_name = _("Medical Cases")

    def ready(self):
        """
        Hook for future signals (case lifecycle, history, notifications).
        """
        # import apps.cases.signals  # يُفعّل لاحقًا عند الحاجة
        pass
