from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

from rest_framework import generics, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    NotificationUpdateSerializer,
)

from apps.appointments.models import Appointment
from apps.accounts.models import User
from medismile.utils.auth import resolve_request_user, require_request_user


# ============================================================
# Pagination
# ============================================================

class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ============================================================
# List & Create
# ============================================================

class NotificationListView(generics.ListCreateAPIView):
    """
    Inbox + notification creation (system/internal only).
    """

    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination

    def get_queryset(self):
        user = resolve_request_user(self.request)

        qs = Notification.objects.select_related(
            "sender",
            "recipient",
            "appointment",
        )

        if not user:
            return Notification.objects.none()

        qs = qs.filter(recipient=user)

        # Optional filters
        params = self.request.query_params

        if params.get("type"):
            qs = qs.filter(notification_type=params["type"])

        if params.get("status"):
            qs = qs.filter(status=params["status"])

        if params.get("is_read") is not None:
            qs = qs.filter(is_read=params["is_read"].lower() == "true")

        if params.get("appointment_id"):
            qs = qs.filter(appointment_id=params["appointment_id"])

        return qs.order_by("-created_at")

    def get_serializer_class(self):
        return (
            NotificationCreateSerializer
            if self.request.method == "POST"
            else NotificationSerializer
        )

    def perform_create(self, serializer):
        serializer.save()


# ============================================================
# Detail / Update (Accept – Reject)
# ============================================================

class NotificationDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve notification + accept/reject requests.
    """

    queryset = Notification.objects.select_related(
        "sender",
        "recipient",
        "appointment",
    )
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return (
            NotificationUpdateSerializer
            if self.request.method in ["PUT", "PATCH"]
            else NotificationSerializer
        )

    def retrieve(self, request, *args, **kwargs):
        notification = self.get_object()
        user = resolve_request_user(request)

        if notification.recipient != user:
            return Response(
                {"error": _("Not authorized")},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])

        return Response(NotificationSerializer(notification).data)

    @transaction.atomic
    def perform_update(self, serializer):
        notification = serializer.save()
        actor = resolve_request_user(self.request)

        if notification.recipient != actor:
            raise serializers.ValidationError(_("Not authorized"))

        # ----------------------------------------------------
        # Appointment Update Accepted
        # ----------------------------------------------------
        if (
            notification.status == "accepted"
            and notification.notification_type == "appointment_update_request"
        ):
            appointment = notification.appointment
            if appointment and notification.proposed_changes:
                for field, value in notification.proposed_changes.items():
                    if hasattr(appointment, field):
                        setattr(appointment, field, value)
                appointment.save()

        # ----------------------------------------------------
        # Appointment Cancel Accepted
        # ----------------------------------------------------
        if (
            notification.status == "accepted"
            and notification.notification_type == "appointment_cancel_request"
        ):
            appointment = notification.appointment
            if appointment:
                appointment.status = Appointment.Status.CANCELLED
                appointment.save()


# ============================================================
# Quick Actions
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_notifications_count(request):
    user = resolve_request_user(request)
    count = Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).count()

    return Response({"unread_count": count})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_as_read(request):
    user = resolve_request_user(request)

    Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).update(is_read=True)

    return Response({"message": _("All notifications marked as read")})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_read_status(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    user = resolve_request_user(request)

    if notification.recipient != user:
        return Response(
            {"error": _("Not authorized")},
            status=status.HTTP_403_FORBIDDEN,
        )

    notification.is_read = not notification.is_read
    notification.save(update_fields=["is_read"])

    return Response(NotificationSerializer(notification).data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    user = resolve_request_user(request)

    if notification.recipient != user:
        return Response(
            {"error": _("Not authorized")},
            status=status.HTTP_403_FORBIDDEN,
        )

    notification.delete()
    return Response({"message": _("Notification deleted")})


# ============================================================
# FCM Token
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_fcm_token(request):
    user = resolve_request_user(request)
    token = request.data.get("fcm_token")

    if not token:
        return Response(
            {"error": _("FCM token is required")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.fcm_token = token
    user.save(update_fields=["fcm_token"])

    return Response({"message": _("FCM token updated")})
