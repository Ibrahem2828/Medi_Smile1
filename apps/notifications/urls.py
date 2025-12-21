
from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    # =====================================================
    # Core
    # =====================================================
    path(
        "",
        views.NotificationListView.as_view(),
        name="notification-list",
    ),
    path(
        "<uuid:pk>/",
        views.NotificationDetailView.as_view(),
        name="notification-detail",
    ),

    # =====================================================
    # Quick Actions
    # =====================================================
    path(
        "actions/unread-count/",
        views.unread_notifications_count,
        name="notifications-unread-count",
    ),
    path(
        "actions/mark-all-read/",
        views.mark_all_as_read,
        name="notifications-mark-all-read",
    ),
    path(
        "<uuid:notification_id>/actions/toggle-read/",
        views.toggle_read_status,
        name="notification-toggle-read",
    ),
    path(
        "<uuid:notification_id>/actions/delete/",
        views.delete_notification,
        name="notification-delete",
    ),

    # =====================================================
    # Device / Push
    # =====================================================
    path(
        "device/fcm-token/",
        views.update_fcm_token,
        name="notification-update-fcm-token",
    ),
]
