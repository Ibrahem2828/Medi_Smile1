from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from .models import Notification
from .serializers import (
    NotificationSerializer, NotificationCreateSerializer, NotificationUpdateSerializer
)
from .utils import create_appointment_notification
from apps.appointments.models import Appointment
from apps.accounts.models import User
from apps.accounts.permissions import IsPatient, IsStudent
from medismile.utils.auth import resolve_request_user, require_request_user


class NotificationPagination(PageNumberPagination):
    """Pagination for notifications."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationListView(generics.ListCreateAPIView):
    """API view for listing and creating notifications."""
    
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_queryset(self):
        """Get notifications for the current user or by explicit filters."""
        user = resolve_request_user(self.request)
        recipient_id = self.request.query_params.get('recipient_id')
        notification_type = self.request.query_params.get('type')
        status_filter = self.request.query_params.get('status')
        is_read = self.request.query_params.get('is_read')
        appointment_id = self.request.query_params.get('appointment_id')
        sender_id = self.request.query_params.get('sender_id')
        
        if recipient_id:
            notifications = Notification.objects.filter(recipient_id=recipient_id)
        elif user:
            notifications = Notification.objects.filter(recipient=user)
        else:
            notifications = Notification.objects.all()
        
        # Filter by type
        if notification_type:
            notifications = notifications.filter(notification_type=notification_type)
        
        # Filter by status
        if status_filter:
            notifications = notifications.filter(status=status_filter)
        
        # Filter by read status
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            notifications = notifications.filter(is_read=is_read_bool)
        
        # Filter by appointment
        if appointment_id:
            notifications = notifications.filter(appointment_id=appointment_id)
        
        # Filter by sender
        if sender_id:
            notifications = notifications.filter(sender_id=sender_id)
        
        return notifications
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == 'POST':
            return NotificationCreateSerializer
        return NotificationSerializer
    
    def perform_create(self, serializer):
        """Create a new notification."""
        serializer.save()


class NotificationDetailView(generics.RetrieveUpdateAPIView):
    """API view for retrieving and updating a notification."""
    
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method in ['PUT', 'PATCH']:
            return NotificationUpdateSerializer
        return NotificationSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Mark notification as read when retrieved."""
        acting_user = resolve_request_user(request)
        instance = self.get_object()
        
        # Check if user is the recipient
        if acting_user and instance.recipient != acting_user:
            return Response({
                'error': _('You are not authorized to view this notification')
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Mark as read
        if not instance.is_read:
            instance.is_read = True
            instance.save(update_fields=['is_read'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def perform_update(self, serializer):
        """Update notification status and handle appointment changes."""
        notification = serializer.save()
        
        # If notification is accepted and it's an update request, apply changes
        if notification.status == 'accepted' and notification.notification_type == 'appointment_update_request':
            if notification.appointment and notification.proposed_changes:
                with transaction.atomic():
                    appointment = notification.appointment
                    
                    # Apply proposed changes
                    for field, value in notification.proposed_changes.items():
                        if hasattr(appointment, field):
                            setattr(appointment, field, value)
                    
                    appointment.save()
                    
                    # Create confirmation notification
                    create_appointment_notification(
                        appointment=appointment,
                        notification_type='appointment_confirmed',
                        sender=notification.recipient,
                        recipient=notification.sender,
                        title=_('Appointment Update Accepted'),
                        message=_('Your appointment update request has been accepted.'),
                        status='accepted'
                    )
        
        # If notification is accepted and it's a cancel request
        elif notification.status == 'accepted' and notification.notification_type == 'appointment_cancel_request':
            if notification.appointment:
                with transaction.atomic():
                    appointment = notification.appointment
                    appointment.status = 'cancelled'
                    appointment.save()
                    
                    # Create confirmation notification
                    create_appointment_notification(
                        appointment=appointment,
                        notification_type='appointment_cancelled',
                        sender=notification.recipient,
                        recipient=notification.sender,
                        title=_('Appointment Cancellation Accepted'),
                        message=_('Your appointment cancellation request has been accepted.'),
                        status='accepted'
                    )
        
        # If notification is rejected, notify the sender
        elif notification.status == 'rejected':
            response_message = notification.response_message or _('Your request has been rejected.')
            create_appointment_notification(
                appointment=notification.appointment,
                notification_type='appointment_cancelled' if notification.notification_type == 'appointment_cancel_request' else 'appointment_cancelled',
                sender=notification.recipient,
                recipient=notification.sender,
                title=_('Request Rejected'),
                message=response_message,
                status='rejected'
            )


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def request_appointment_update(request, appointment_id):
    """Request appointment update from patient/student."""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return Response({
            'error': _('Appointment not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user, error = require_request_user(request, error_key='user_id')
    if error:
        return error
    
    # Check if user is part of the appointment
    if user.role == 'patient' and appointment.patient != user:
        return Response({
            'error': _('You are not authorized to request update for this appointment')
        }, status=status.HTTP_403_FORBIDDEN)
    
    if appointment.user != user:
        return Response({
            'error': _('You are not authorized to request update for this appointment')
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Determine recipient (the other party)
    recipient = appointment.user if user.role == 'patient' else appointment.patient
    
    # Get proposed changes from request
    proposed_changes = request.data.get('proposed_changes', {})
    message = request.data.get('message', '')
    title = request.data.get('title', _('Appointment Update Request'))
    
    # Create notification
    notification = Notification.objects.create(
        sender=user,
        recipient=recipient,
        notification_type='appointment_update_request',
        appointment=appointment,
        title=title,
        message=message,
        proposed_changes=proposed_changes,
        status='pending'
    )
    
    serializer = NotificationSerializer(notification)
    return Response({
        'message': _('Appointment update request sent successfully'),
        'notification': serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def unread_notifications_count(request):
    """Get count of unread notifications for current user."""
    user = resolve_request_user(request)
    recipient_id = request.query_params.get('recipient_id')
    
    if recipient_id:
        count = Notification.objects.filter(recipient_id=recipient_id, is_read=False).count()
    elif user:
        count = Notification.objects.filter(recipient=user, is_read=False).count()
    else:
        count = Notification.objects.filter(is_read=False).count()
    
    return Response({
        'unread_count': count
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def request_appointment_cancel(request, appointment_id):
    """Request appointment cancellation from patient/student."""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return Response({
            'error': _('Appointment not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user, error = require_request_user(request, error_key='user_id')
    if error:
        return error
    
    # Check if user is part of the appointment
    if user.role == 'patient' and appointment.patient != user:
        return Response({
            'error': _('You are not authorized to request cancellation for this appointment')
        }, status=status.HTTP_403_FORBIDDEN)
    
    if appointment.user != user:
        return Response({
            'error': _('You are not authorized to request cancellation for this appointment')
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if appointment can be cancelled
    if appointment.status in ['cancelled', 'completed']:
        return Response({
            'error': _('Appointment cannot be cancelled')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Determine recipient (the other party)
    recipient = appointment.user if user.role == 'patient' else appointment.patient
    
    # Get message from request
    message = request.data.get('message', _('I would like to cancel this appointment.'))
    title = request.data.get('title', _('Appointment Cancellation Request'))
    
    # Create notification
    notification = create_appointment_notification(
        appointment=appointment,
        notification_type='appointment_cancel_request',
        sender=user,
        recipient=recipient,
        title=title,
        message=message,
        status='pending'
    )
    
    serializer = NotificationSerializer(notification)
    return Response({
        'message': _('Appointment cancellation request sent successfully'),
        'notification': serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def mark_all_as_read(request):
    """Mark all notifications as read for current user."""
    user = resolve_request_user(request)
    recipient_id = request.data.get('recipient_id') or request.query_params.get('recipient_id')
    
    if recipient_id:
        Notification.objects.filter(recipient_id=recipient_id, is_read=False).update(is_read=True)
    elif user:
        Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
    else:
        Notification.objects.all().update(is_read=True)
    
    return Response({
        'message': _('All notifications marked as read')
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def toggle_read_status(request, notification_id):
    """Toggle read status of a notification."""
    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return Response({
            'error': _('Notification not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = resolve_request_user(request)
    
    # Check if user is the recipient when user context is available
    if user and notification.recipient != user:
        return Response({
            'error': _('You are not authorized to modify this notification')
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Toggle read status
    notification.is_read = not notification.is_read
    notification.save(update_fields=['is_read'])
    
    serializer = NotificationSerializer(notification)
    return Response({
        'message': _('Notification read status updated successfully'),
        'notification': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def delete_notification(request, notification_id):
    """Delete a notification."""
    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return Response({
            'error': _('Notification not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = resolve_request_user(request)
    
    # Check if user is the recipient when user context is available
    if user and notification.recipient != user:
        return Response({
            'error': _('You are not authorized to delete this notification')
        }, status=status.HTTP_403_FORBIDDEN)
    
    notification.delete()
    
    return Response({
        'message': _('Notification deleted successfully')
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def update_fcm_token(request):
    """Update FCM token for current user."""
    user = resolve_request_user(request)
    if not user:
        user_id = request.data.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'error': _('User not found')
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({
                'error': _('user_id is required when authentication is disabled')
            }, status=status.HTTP_400_BAD_REQUEST)
    fcm_token = request.data.get('fcm_token')
    
    if not fcm_token:
        return Response({
            'error': _('FCM token is required')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user.fcm_token = fcm_token
    user.save(update_fields=['fcm_token'])
    
    return Response({
        'message': _('FCM token updated successfully'),
        'fcm_token': user.fcm_token
    }, status=status.HTTP_200_OK)


