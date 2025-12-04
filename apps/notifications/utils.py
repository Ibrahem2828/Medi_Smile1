"""
Helper functions for creating notifications automatically.
"""
from django.utils.translation import gettext_lazy as _
from .models import Notification
from .services import send_notification_to_user


def create_appointment_notification(
    appointment,
    notification_type: str,
    sender,
    recipient,
    title: str = None,
    message: str = None,
    proposed_changes: dict = None,
    status: str = 'accepted'
) -> Notification:
    """
    Create an appointment-related notification.
    
    Args:
        appointment: Appointment object
        notification_type: Type of notification
        sender: User who sends the notification
        recipient: User who receives the notification
        title: Notification title (optional)
        message: Notification message (optional)
        proposed_changes: Proposed changes for update requests (optional)
        status: Notification status (default: 'accepted')
    
    Returns:
        Notification: Created notification object
    """
    # Default titles and messages based on type
    default_titles = {
        'appointment_confirmed': _('Appointment Confirmed'),
        'appointment_cancelled': _('Appointment Cancelled'),
        'appointment_completed': _('Appointment Completed'),
        'appointment_update_request': _('Appointment Update Request'),
        'appointment_cancel_request': _('Appointment Cancel Request'),
    }
    
    default_messages = {
        'appointment_confirmed': _('Your appointment has been confirmed.'),
        'appointment_cancelled': _('Your appointment has been cancelled.'),
        'appointment_completed': _('Your appointment has been completed.'),
        'appointment_update_request': _('You have received an appointment update request.'),
        'appointment_cancel_request': _('You have received an appointment cancellation request.'),
    }
    
    notification = Notification.objects.create(
        sender=sender,
        recipient=recipient,
        notification_type=notification_type,
        appointment=appointment,
        title=title or default_titles.get(notification_type, _('Notification')),
        message=message or default_messages.get(notification_type, _('You have a new notification.')),
        proposed_changes=proposed_changes,
        status=status
    )
    
    # Send push notification
    try:
        send_notification_to_user(recipient, notification)
    except Exception as e:
        print(f"Error sending push notification: {e}")
    
    return notification


def notify_appointment_status_change(
    appointment,
    old_status: str,
    new_status: str,
    changed_by
):
    """
    Create automatic notification when appointment status changes.
    
    Args:
        appointment: Appointment object
        old_status: Previous status
        new_status: New status
        changed_by: User who made the change
    """
    # Determine recipient (the other party)
    if changed_by == appointment.patient:
        recipient = appointment.user
    else:
        recipient = appointment.patient
    
    # Map status changes to notification types
    status_to_notification_type = {
        'confirmed': 'appointment_confirmed',
        'cancelled': 'appointment_cancelled',
        'completed': 'appointment_completed',
    }
    
    notification_type = status_to_notification_type.get(new_status)
    if not notification_type:
        return None
    
    # Create notification
    return create_appointment_notification(
        appointment=appointment,
        notification_type=notification_type,
        sender=changed_by,
        recipient=recipient,
        status='accepted'
    )
















