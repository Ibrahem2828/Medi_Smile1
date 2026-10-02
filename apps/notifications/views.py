# apps/notifications/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from drf_spectacular.utils import extend_schema

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
    permission_ownership_checker = staticmethod(is_notification_recipient)
    permission_scope_checker = staticmethod(is_same_university)

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

    @extend_schema(request=NotificationCreateSerializer, responses={201: NotificationSerializer})
    def create(self, request, *args, **kwargs):
        # Respond with the full read representation (including ``id``) so
        # clients don't have to re-fetch the inbox to find what they created.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification = serializer.save()
        return Response(
            NotificationSerializer(notification, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


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
    permission_ownership_checker = staticmethod(is_notification_recipient)
    permission_scope_checker = staticmethod(is_same_university)

    def get_object(self):
        return super().get_object()

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response(response.data, status=status.HTTP_200_OK)
