# apps/messaging/urls.py
from django.urls import path

from .views import (
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
