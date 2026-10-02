from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.db import DatabaseError, connections
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView

from medismile.ui_views import ui_index, ui_contract

admin.site.site_header = "MediSmile Admin"
admin.site.site_title = "MediSmile Admin"
admin.site.index_title = "Administration"


# ============================================================
# System / Health
# ============================================================

def health_check(request):
    """
    Simple health check endpoint.

    Used by:
    - Load balancers
    - Railway / Docker
    - Monitoring systems
    """
    return JsonResponse({
        "status": "ok",
        "service": "medismile-backend",
        "version": "v1"
    })


def readiness_check(request):
    """Return ready only when this instance can serve database-backed APIs.

    Keep this deliberately independent from AI model services: a slow model
    must not make account, case, and appointment traffic look unavailable.
    Coolify should use this endpoint as the application's health check.
    """
    try:
        connection = connections["default"]
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse(
            {"status": "unavailable", "service": "medismile-backend"},
            status=503,
        )
    return JsonResponse({"status": "ready", "service": "medismile-backend"})


# ============================================================
# API Versioning
# ============================================================

API_V1_PREFIX = "api/"


urlpatterns = [

    # --------------------------------------------------------
    # Django Admin
    # --------------------------------------------------------
    path("admin/", admin.site.urls),

    # --------------------------------------------------------
    # System Endpoints
    # --------------------------------------------------------
    path("health/", health_check, name="health-check"),
    path("readyz/", readiness_check, name="readiness-check"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("ui/", ui_index, name="ui-index"),
    path("ui/contracts/<slug:contract>/", ui_contract, name="ui-contract"),

    # --------------------------------------------------------
    # API v1 - Core Accounts & Identity
    # --------------------------------------------------------
    path(f"{API_V1_PREFIX}accounts/", include("apps.accounts.urls")),

    # --------------------------------------------------------
    # API v1 - Academic Structure
    # --------------------------------------------------------
    path(f"{API_V1_PREFIX}universities/", include("apps.universities.urls")),

    # --------------------------------------------------------
    # API v1 - Medical Core
    # --------------------------------------------------------
    path(f"{API_V1_PREFIX}cases/", include("apps.cases.urls")),
    path(f"{API_V1_PREFIX}appointments/", include("apps.appointments.urls")),
    path(f"{API_V1_PREFIX}evaluations/", include("apps.evaluations.urls")),

    # --------------------------------------------------------
    # API v1 - AI Services
    # --------------------------------------------------------
    path(f"{API_V1_PREFIX}ai/", include("apps.ai.urls")),

    # --------------------------------------------------------
    # API v1 - Communication & Community
    # --------------------------------------------------------
    path(f"{API_V1_PREFIX}messaging/", include("apps.messaging.urls")),
    path(f"{API_V1_PREFIX}community/", include("apps.community.urls")),
    path(f"{API_V1_PREFIX}notifications/", include("apps.notifications.urls")),

    # --------------------------------------------------------
    # API v1 - Files & Attachments
    # --------------------------------------------------------
    path(f"{API_V1_PREFIX}attachments/", include("apps.attachments.urls")),

    # --------------------------------------------------------
    # API v1 - System & Governance
    # --------------------------------------------------------
    path(f"{API_V1_PREFIX}audit/", include("apps.audit.urls")),
    path(f"{API_V1_PREFIX}reports/", include("apps.reports.urls")),
    path(f"{API_V1_PREFIX}backup/", include("apps.backup.urls")),
    path(f"{API_V1_PREFIX}support/", include("apps.support.urls")),

    # --------------------------------------------------------
    # Future versions (placeholder)
    # --------------------------------------------------------
    # path("api/v2/", include("medismile.api.v2.urls")),
]


# ============================================================
# Static & Media (Development only)
# ============================================================
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
