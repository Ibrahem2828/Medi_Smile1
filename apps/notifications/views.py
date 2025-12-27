# apps/notifications/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from medismile.permissions import MatrixPermission
from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    NotificationUpdateSerializer,
)
from .permissions import is_notification_recipient, is_same_university
from .utils import can_user_read_notification


# ============================================================
# Inbox
# ============================================================
class NotificationListView(generics.ListAPIView):
    """
    List notifications for the authenticated user.
    """
    serializer_class = NotificationSerializer
    permission_classes = [MatrixPermission]
    permission_resource = "notifications.notification"
    permission_action = "view"
    permission_ownership_checker = lambda user, obj: is_notification_recipient(user, obj)  # type: ignore
    permission_scope_checker = lambda user, obj: is_same_university(user, obj)  # type: ignore

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
    permission_classes = [MatrixPermission]
    permission_resource = "notifications.notification"
    permission_action = "create"


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
    permission_classes = [MatrixPermission]
    permission_resource = "notifications.notification"
    permission_action = "update"
    permission_ownership_checker = lambda user, obj: is_notification_recipient(user, obj)  # type: ignore
    permission_scope_checker = lambda user, obj: is_same_university(user, obj)  # type: ignore

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj)

        return obj

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response(response.data, status=status.HTTP_200_OK)
