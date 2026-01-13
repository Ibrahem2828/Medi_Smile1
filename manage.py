#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def _ensure_venv():
    if os.getenv("VIRTUAL_ENV"):
        return
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if os.name == "nt":
        venv_python = os.path.join(base_dir, "venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join(base_dir, "venv", "bin", "python")
    if os.path.exists(venv_python):
        if os.path.abspath(sys.executable) != os.path.abspath(venv_python):
            os.execv(venv_python, [venv_python] + sys.argv)


def main():
    """Run administrative tasks."""
    _ensure_venv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medismile.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
