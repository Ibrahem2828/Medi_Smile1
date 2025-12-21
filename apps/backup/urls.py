from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import BackupViewSet


# ============================================================
# Router
# ============================================================

router = DefaultRouter()
router.register(
    r"backups",
    BackupViewSet,
    basename="backup",
)


# ============================================================
# URLs
# ============================================================

urlpatterns = [
    path("", include(router.urls)),
]
