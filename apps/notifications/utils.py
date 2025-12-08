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


def create_content_approval_notification(content):
    """
    Create notification to supervisors when a student creates content.
    
    Args:
        content: Content object created by student
    """
    from apps.accounts.models import User
    
    # Get all supervisors from the same university
    supervisors = User.objects.filter(role='supervisor')
    
    if content.university:
        # Filter supervisors from same university
        supervisors = supervisors.filter(
            supervisorprofile__university=content.university
        )
    
    if not supervisors.exists():
        # If no supervisors, notify university admins
        supervisors = User.objects.filter(
            role='university_admin',
            universityadminprofile__university=content.university
        ) if content.university else User.objects.filter(role='university_admin')
    
    # Create notification for each supervisor/admin
    notifications = []
    for supervisor in supervisors:
        notification = Notification.objects.create(
            sender=content.author,
            recipient=supervisor,
            notification_type='content_approval_request',
            content=content,
            title=_('New Content Approval Request'),
            message=_('Student {student_name} has created a new post "{title}" that requires your approval.').format(
                student_name=content.author.get_full_name() or content.author.username,
                title=content.title
            ),
            status='pending'
        )
        
        # Send push notification
        try:
            send_notification_to_user(supervisor, notification)
        except Exception as e:
            print(f"Error sending push notification: {e}")
        
        notifications.append(notification)
    
    return notifications


def create_content_approved_notification(content, approved_by):
    """
    Create notification to student when content is approved.
    
    Args:
        content: Content object that was approved
        approved_by: User who approved the content
    """
    notification = Notification.objects.create(
        sender=approved_by,
        recipient=content.author,
        notification_type='content_approved',
        content=content,
        title=_('Content Approved'),
        message=_('Your post "{title}" has been approved and is now visible to the community.').format(
            title=content.title
        ),
        status='accepted'
    )
    
    # Send push notification
    try:
        send_notification_to_user(content.author, notification)
    except Exception as e:
        print(f"Error sending push notification: {e}")
    
    return notification


def create_content_rejected_notification(content, rejected_by, rejection_reason):
    """
    Create notification to student when content is rejected.
    
    Args:
        content: Content object that was rejected
        rejected_by: User who rejected the content
        rejection_reason: Reason for rejection
    """
    message = _('Your post "{title}" has been rejected.').format(title=content.title)
    if rejection_reason:
        message += f" {_('Reason')}: {rejection_reason}"
    
    notification = Notification.objects.create(
        sender=rejected_by,
        recipient=content.author,
        notification_type='content_rejected',
        content=content,
        title=_('Content Rejected'),
        message=message,
        status='rejected',
        response_message=rejection_reason
    )
    
    # Send push notification
    try:
        send_notification_to_user(content.author, notification)
    except Exception as e:
        print(f"Error sending push notification: {e}")
    
    return notification



















