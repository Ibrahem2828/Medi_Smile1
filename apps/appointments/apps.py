# apps/appointments/apps.py
from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    """
    Appointments app configuration.

    Responsibilities:
    - Scheduling and managing clinical appointments.
    - Enforcing student-led scheduling workflow.
    - Integrating with:
        * cases (ownership & lifecycle)
        * accounts (role-based access)
        * notifications (reminders & alerts)
        * audit (activity logging)

    This app intentionally avoids heavy logic here;
    business rules live in models & serializers.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.appointments"
    verbose_name = "Appointments"

    def ready(self):
        """
        Hook for future integrations:
        - Signals for appointment creation/update
        - Notification scheduling (Celery)
        - Audit trail logging
        """
        # from . import signals  # noqa: F401
        pass
