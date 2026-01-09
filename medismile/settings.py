from datetime import timedelta
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
import dj_database_url

# ============================================================
# Base
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()  # تحميل متغيرات البيئة عند العمل محليًا

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "*,medismile1-production.up.railway.app"
).split(",")

# ============================================================
# Applications
# ============================================================
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "corsheaders",
    "channels",
    "apps.accounts.apps.AccountsConfig",
    "apps.universities",
    "apps.cases",
    "apps.ai",
    "apps.appointments",
    "apps.evaluations",
    "apps.messaging",
    "apps.community",
    "apps.attachments",
    "apps.audit",
    "apps.notifications",
    "apps.reports",
    "apps.backup",
    "apps.support",
]

# ============================================================
# Middleware
# ============================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ============================================================
# URLs / Templates
# ============================================================
ROOT_URLCONF = "medismile.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "medismile.wsgi.application"
ASGI_APPLICATION = "medismile.asgi.application"

# ============================================================
# Custom User Model
# ============================================================
AUTH_USER_MODEL = "accounts.User"

# ============================================================
# Channels (WebSocket)
# ============================================================
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (
                    os.getenv("REDIS_HOST", "127.0.0.1"),
                    int(os.getenv("REDIS_PORT", 6379)),
                )
            ],
        },
    },
}

# ============================================================
# Database (PostgreSQL)
# ============================================================
"""
Strategy:
- Local development → PostgreSQL localhost
- Production / Railway → DATABASE_URL
"""

database_url = os.getenv("DATABASE_URL")
if database_url:
    # Production / Cloud (with optional sqlite override for local/test)
    DATABASES = {
        "default": dj_database_url.parse(
            database_url,
            conn_max_age=600,
            ssl_require=not database_url.startswith("sqlite"),
        )
    }
else:
    # Localhost PostgreSQL
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "medismile_db"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

# ============================================================
# Password Validation
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================================
# Language & Time
# ============================================================
LANGUAGE_CODE = "ar"
TIME_ZONE = "Asia/Riyadh"
USE_I18N = True
USE_TZ = True

# ============================================================
# Static & Media
# ============================================================
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

# ============================================================
# REST Framework
# ============================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "EXCEPTION_HANDLER": "medismile.utils.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "ai-diagnose": "5/minute",
        "ai-review": "30/hour",
        "ai-health": "120/hour",
        "ai-my-analysis": "30/hour",
    },
}



# ============================================================
# Simple JWT
# ============================================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=20),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}


# AI Engines (external)
AI_SYMPTOMS_URL = os.getenv("AI_SYMPTOMS_URL", "")
AI_VISION_URL = os.getenv("AI_VISION_URL", "")
AI_FUSION_URL = os.getenv("AI_FUSION_URL", "")
AI_ENGINE_BASE_URL = os.getenv("AI_ENGINE_BASE_URL", "")  # Only for local/dev if explicitly set
AI_ENGINE_TIMEOUT = int(os.getenv("AI_ENGINE_TIMEOUT", "30"))

# Enforce explicit endpoints in non-debug environments to avoid localhost fallback.
if not DEBUG:
    _required_ai_vars = {
        "AI_SYMPTOMS_URL": AI_SYMPTOMS_URL,
        "AI_VISION_URL": AI_VISION_URL,
        "AI_FUSION_URL": AI_FUSION_URL,
    }
    _missing_ai = [name for name, value in _required_ai_vars.items() if not value]
    if _missing_ai:
        raise ImproperlyConfigured(f"Missing AI endpoint configuration: {', '.join(_missing_ai)}")


# ============================================================
# CORS
# ============================================================
CORS_ALLOW_ALL_ORIGINS = True

# ============================================================
# Logging
# ============================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# ============================================================
# Celery
# ============================================================
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# ============================================================
# Backup
# ============================================================
BACKUP_DIRECTORY = str(BASE_DIR / "backups")
BACKUP_STORAGE_TYPE = os.getenv("BACKUP_STORAGE_TYPE", "local")  # local | s3
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
