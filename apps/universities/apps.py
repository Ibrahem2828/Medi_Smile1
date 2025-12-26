# apps/universities/apps.py
from django.apps import AppConfig


class UniversitiesConfig(AppConfig):
    """
    Universities app config.

    - Holds organizational scope (University) and academic structures.
    - Provides the base for university scoping used across the platform.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.universities"
    verbose_name = "Universities"
