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

def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() == "true"


def _env_list(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


DEBUG = _env_bool("DEBUG")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be configured when DEBUG=False.")
    SECRET_KEY = "dev-secret-key"

EXPOSE_ERROR_DETAILS = DEBUG and _env_bool("EXPOSE_ERROR_DETAILS")

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    if DEBUG:
        ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
    else:
        raise ImproperlyConfigured("ALLOWED_HOSTS must be configured when DEBUG=False.")

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
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
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
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
redis_url = os.getenv("REDIS_URL")
redis_hosts = [redis_url] if redis_url else [
    (
        os.getenv("REDIS_HOST", "127.0.0.1"),
        int(os.getenv("REDIS_PORT", "6379")),
    )
]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": redis_hosts,
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
    database_ssl_require = _env_bool(
        "DATABASE_SSL_REQUIRE", default=not DEBUG
    )
    # Production / Cloud (with optional sqlite override for local/test)
    DATABASES = {
        "default": dj_database_url.parse(
            database_url,
            conn_max_age=int(os.getenv("DATABASE_CONN_MAX_AGE", "600")),
            # Coolify services normally communicate on an isolated Docker
            # network, where TLS is not terminated by PostgreSQL itself. A
            # public/managed database should set DATABASE_SSL_REQUIRE=true.
            ssl_require=(False if database_url.startswith("sqlite") else database_ssl_require),
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

DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

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
# ``MEDIA_ROOT`` is retained only for non-medical, explicitly public assets.
# Uploaded clinical images, attachments and report exports use the private
# storage configured below and must never be mounted by a reverse proxy.
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_MEDIA_ROOT = Path(os.getenv("PRIVATE_MEDIA_ROOT", str(BASE_DIR / "private_media")))

_storage_backend = os.getenv(
    "PRIVATE_FILE_STORAGE_BACKEND", "django.core.files.storage.FileSystemStorage"
)
STORAGES = {
    "default": {
        "BACKEND": _storage_backend,
        "OPTIONS": (
            {"location": PRIVATE_MEDIA_ROOT, "base_url": "/private-media/"}
            if _storage_backend == "django.core.files.storage.FileSystemStorage"
            else {}
        ),
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_USE_FINDERS = True

# ============================================================
# Reports PDF Rendering
# ============================================================
_reports_font_dir = BASE_DIR / "static" / "fonts"
_reports_cairo = _reports_font_dir / "Cairo-Regular.ttf"
_reports_cairo_bold = _reports_font_dir / "Cairo-Bold.ttf"
_reports_tahoma = _reports_font_dir / "tahoma.ttf"
_reports_tahoma_bold = _reports_font_dir / "tahomabd.ttf"

REPORTS_PDF_FONT_PATH = os.getenv(
    "REPORTS_PDF_FONT_PATH",
    str(_reports_cairo if _reports_cairo.exists() else _reports_tahoma),
)
REPORTS_PDF_BOLD_FONT_PATH = os.getenv(
    "REPORTS_PDF_BOLD_FONT_PATH",
    str(_reports_cairo_bold if _reports_cairo_bold.exists() else _reports_tahoma_bold),
)
REPORTS_MEDISMILE_LOGO = os.getenv("REPORTS_MEDISMILE_LOGO", "")

if not REPORTS_MEDISMILE_LOGO:
    REPORTS_MEDISMILE_LOGO = str(
        BASE_DIR / "static" / "rest_framework" / "img" / "Medismile.jpg"
    )

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
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/hour",
        "user": "1200/hour",
        "login": "10/minute",
        "ai-diagnose": "5/minute",
        "ai-image-upload": "20/minute",
        "ai-review": "30/hour",
        "ai-health": "120/hour",
        "ai-my-analysis": "30/hour",
        "messaging": "60/minute",
    },
}



# ============================================================
# OpenAPI (drf-spectacular)
# ============================================================
# The committed spec at docs/api/openapi.yaml is generated from the code:
#   python manage.py spectacular --file docs/api/openapi.yaml --validate
# and medismile/test_openapi_contract.py fails if it drifts from the code.
SPECTACULAR_SETTINGS = {
    "TITLE": "MediSmile API",
    "DESCRIPTION": (
        "REST API of the MediSmile dental training & consultation platform. "
        "All endpoints are under /api/ and authenticate with `Authorization: Bearer <JWT access token>` "
        "obtained from /api/accounts/login/<role>/."
    ),
    "VERSION": "1.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/",
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "PREPROCESSING_HOOKS": ["medismile.openapi.exclude_slashless_aliases"],
    # The schema itself is not secret, but keep the live endpoint staff-only
    # in production; the committed YAML is the reference for clients.
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
}


# ============================================================
# Simple JWT
# ============================================================
SIMPLE_JWT = {
    # Access tokens are intentionally short-lived.  The refresh token is
    # rotated and blacklisted on use; logout blacklists it as well.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
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

# Patient image uploads for AI analysis (POST /api/ai/images/, /api/ai/diagnose/)
AI_IMAGE_MAX_BYTES = int(os.getenv("AI_IMAGE_MAX_BYTES", str(10 * 1024 * 1024)))
AI_IMAGE_MAX_PIXELS = int(os.getenv("AI_IMAGE_MAX_PIXELS", "40000000"))
AI_IMAGE_MAX_SIDE = int(os.getenv("AI_IMAGE_MAX_SIDE", "2048"))
# Legacy image_urls input: the backend fetches these URLs, so only explicitly
# trusted HTTPS hosts are accepted (empty = URL input disabled; use uploads).
AI_IMAGE_URL_ALLOWED_HOSTS = _env_list("AI_IMAGE_URL_ALLOWED_HOSTS")

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
CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = DEBUG and not CORS_ALLOWED_ORIGINS

if not DEBUG and not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS must be configured when DEBUG=False."
    )

# ============================================================
# CSRF / Security (Production)
# ============================================================
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")
if not DEBUG and not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured(
        "CSRF_TRUSTED_ORIGINS must be configured when DEBUG=False."
    )

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = _env_bool("CSRF_COOKIE_SECURE", default=not DEBUG)
SECURE_HSTS_SECONDS = int(
    os.getenv("SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG
)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

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
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL", redis_url or "redis://127.0.0.1:6379/0"
)
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND", redis_url or "redis://127.0.0.1:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# ============================================================
# Backup
# ============================================================
BACKUP_DIRECTORY = os.getenv("BACKUP_DIRECTORY", str(BASE_DIR / "backups"))
BACKUP_STORAGE_TYPE = os.getenv("BACKUP_STORAGE_TYPE", "local")  # local | s3
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
# Restore is deliberately disabled by default.  A real restore is destructive
# and must target a separate, explicitly configured recovery environment.
BACKUP_RESTORE_ENABLED = _env_bool("BACKUP_RESTORE_ENABLED")
BACKUP_RESTORE_DATABASE_URL = os.getenv("BACKUP_RESTORE_DATABASE_URL", "")
BACKUP_RESTORE_MEDIA_ROOT = os.getenv("BACKUP_RESTORE_MEDIA_ROOT", "")

# Attachment input policy. Content is verified from bytes, not the client MIME
# header, before it is written to private storage.
ATTACHMENT_MAX_BYTES = int(os.getenv("ATTACHMENT_MAX_BYTES", str(10 * 1024 * 1024)))
