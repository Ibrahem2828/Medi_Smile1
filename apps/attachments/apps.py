# apps/attachments/apps.py
from django.apps import AppConfig


class AttachmentsConfig(AppConfig):
    """
    Attachments app configuration.

    Responsibilities:
    - Manage medical & educational attachments.
    - Store before/after images and reports.
    - Integrate with:
        * appointments (primary linkage)
        * cases (medical context)
        * accounts (role-based access)
        * storage backends (local / S3)

    No business logic lives here.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.attachments"
    verbose_name = "Attachments"

    def ready(self):
        """
        Future hooks:
        - Signals for upload/delete
        - Audit logging
        - Notification triggers
        """
        # from . import signals  # noqa: F401
        pass
