"""
WSGI config for medismile project.

This module exposes the WSGI callable as a module-level variable named `application`.

It is used by WSGI servers such as:
- Gunicorn
- uWSGI
- Railway / Heroku-style platforms

Docs:
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application


# ============================================================
# Django settings
# ============================================================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medismile.settings")


# ============================================================
# WSGI application
# ============================================================
application = get_wsgi_application()
