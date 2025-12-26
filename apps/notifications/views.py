# apps/notifications/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    NotificationUpdateSerializer,
)
from .utils import can_user_read_notification


# ============================================================
# Inbox
# ============================================================
class NotificationListView(generics.ListAPIView):
    """
    List notifications for the authenticated user.
    """
    serializer_class = NotificationSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Notification.objects.select_related(
            "sender",
            "recipient",
            "appointment",
        )

        # User inbox
        return qs.filter(recipient=user)


# ============================================================
# Create (internal / service-driven)
# ============================================================
class NotificationCreateView(generics.CreateAPIView):
    """
    Create notifications (used by system / workflows).
    """
    serializer_class = NotificationCreateSerializer


# ============================================================
# Detail & Update
# ============================================================
class NotificationDetailUpdateView(generics.RetrieveUpdateAPIView):
    """
    Retrieve / update notification:
    - Mark as read
    - Accept / Reject requests
    """
    queryset = Notification.objects.select_related(
        "sender",
        "recipient",
        "appointment",
    )
    serializer_class = NotificationUpdateSerializer

    def get_object(self):
        obj = super().get_object()
        user = self.request.user

        if not can_user_read_notification(user, obj):
            raise PermissionDenied("You are not allowed to access this notification.")

        return obj

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response(response.data, status=status.HTTP_200_OK)
