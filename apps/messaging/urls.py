# apps/messaging/urls.py
from django.urls import path

from .views import (
    RoomListView,
    RoomRetrieveView,
    RoomCreateView,
    MessageListCreateView,
    MessageDetailView,
)

urlpatterns = [
    # =====================================================
    # Rooms (Case Conversations)
    # =====================================================
    path(
        "threads/",
        RoomListView.as_view(),
        name="messaging-room-list",
    ),
    path(
        "threads/<uuid:pk>/",
        RoomRetrieveView.as_view(),
        name="messaging-room-detail-thread-alias",
    ),
    path(
        "threads/<uuid:room_id>/messages/",
        MessageListCreateView.as_view(),
        name="message-list-create-thread-alias",
    ),
    path(
        "rooms/<uuid:pk>/",
        RoomRetrieveView.as_view(),
        name="messaging-room-detail",
    ),
    path(
        "rooms/",
        RoomCreateView.as_view(),
        name="messaging-room-create",
    ),

    # =====================================================
    # Messages
    # =====================================================
    path(
        "rooms/<uuid:room_id>/messages/",
        MessageListCreateView.as_view(),
        name="message-list-create",
    ),
    path(
        "messages/<uuid:pk>/",
        MessageDetailView.as_view(),
        name="message-detail",
    ),
]
