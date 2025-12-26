# apps/notifications/urls.py
from django.urls import path

from .views import (
    NotificationListView,
    NotificationCreateView,
    NotificationDetailUpdateView,
)

app_name = "notifications"

urlpatterns = [
    # =========================================================
    # Inbox
    # =========================================================
    path(
        "",
        NotificationListView.as_view(),
        name="notification-list",
    ),

    # =========================================================
    # Create (system / internal use)
    # =========================================================
    path(
        "create/",
        NotificationCreateView.as_view(),
        name="notification-create",
    ),

    # =========================================================
    # Detail & Update
    # =========================================================
    path(
        "<uuid:pk>/",
        NotificationDetailUpdateView.as_view(),
        name="notification-detail",
    ),
]
