from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('<uuid:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('appointments/<uuid:appointment_id>/request-update/', views.request_appointment_update, name='request-appointment-update'),
    path('appointments/<uuid:appointment_id>/request-cancel/', views.request_appointment_cancel, name='request-appointment-cancel'),
    path('unread-count/', views.unread_notifications_count, name='unread-notifications-count'),
    path('mark-all-read/', views.mark_all_as_read, name='mark-all-read'),
    path('<uuid:notification_id>/toggle-read/', views.toggle_read_status, name='toggle-read-status'),
    path('<uuid:notification_id>/delete/', views.delete_notification, name='delete-notification'),
    path('fcm-token/', views.update_fcm_token, name='update-fcm-token'),
]




