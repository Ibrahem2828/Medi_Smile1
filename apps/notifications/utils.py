"""
Helper functions for creating notifications automatically.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List

from django.utils.translation import gettext_lazy as _

from .models import Notification
from .services import send_notification_to_user


# ============================================================
# Appointment Notifications Helpers
# ============================================================

def create_appointment_notification(
    *,
    appointment,
    notification_type: str,
    sender,
    recipient,
    title: Optional[str] = None,
    message: Optional[str] = None,
    proposed_changes: Optional[Dict[str, Any]] = None,
    status: str = "accepted",
) -> Notification:
    """
    Create an appointment-related notification and (optionally) push it via FCM.

    IMPORTANT:
    - For "request" notifications, status should be "pending".
    - For info notifications (confirmed/cancelled/completed), status can be "accepted".
    """

    default_titles = {
        "appointment_confirmed": _("Appointment Confirmed"),
        "appointment_cancelled": _("Appointment Cancelled"),
        "appointment_completed": _("Appointment Completed"),
        "appointment_update_request": _("Appointment Update Request"),
        "appointment_cancel_request": _("Appointment Cancel Request"),
    }

    default_messages = {
        "appointment_confirmed": _("Your appointment has been confirmed."),
        "appointment_cancelled": _("Your appointment has been cancelled."),
        "appointment_completed": _("Your appointment has been completed."),
        "appointment_update_request": _("You have received an appointment update request."),
        "appointment_cancel_request": _("You have received an appointment cancellation request."),
    }

    notification = Notification.objects.create(
        sender=sender,
        recipient=recipient,
        notification_type=notification_type,
        appointment=appointment,
        title=title or default_titles.get(notification_type, _("Notification")),
        message=message or default_messages.get(notification_type, _("You have a new notification.")),
        proposed_changes=proposed_changes,
        status=status,
    )

    # Push notification (best-effort)
    try:
        send_notification_to_user(recipient, notification)
    except Exception:
        # do not crash main request path
        pass

    return notification


def notify_appointment_status_change(
    *,
    appointment,
    old_status: str,
    new_status: str,
    changed_by,
) -> Optional[Notification]:
    """
    Create automatic notification when appointment status changes.

    Appointment model fields:
    - patient
    - created_by (student/supervisor)

    So "the other party" = patient <-> created_by
    """

    # Determine recipient (the other party)
    if changed_by == appointment.patient:
        recipient = appointment.created_by
    else:
        recipient = appointment.patient

    status_to_notification_type = {
        "confirmed": "appointment_confirmed",
        "cancelled": "appointment_cancelled",
        "completed": "appointment_completed",
    }

    notification_type = status_to_notification_type.get(new_status)
    if not notification_type:
        return None

    return create_appointment_notification(
        appointment=appointment,
        notification_type=notification_type,
        sender=changed_by,
        recipient=recipient,
        status="accepted",
    )


# ============================================================
# Community Content Approval Helpers
# ============================================================

def create_content_approval_notification(content) -> List[Notification]:
    """
    Notify supervisors (same university) that a student post requires approval.
    Falls back to university_admin when no supervisors exist.

    NOTE:
    - This assumes community.Content has:
      - author
      - university (optional)
      - title
    """

    from apps.accounts.models import User

    supervisors = User.objects.filter(role="supervisor")

    if getattr(content, "university", None):
        supervisors = supervisors.filter(
            supervisorprofile__university=content.university
        )

    if not supervisors.exists():
        if getattr(content, "university", None):
            supervisors = User.objects.filter(
                role="university_admin",
                universityadminprofile__university=content.university,
            )
        else:
            supervisors = User.objects.filter(role="university_admin")

    notifications: List[Notification] = []

    for reviewer in supervisors:
        notification = Notification.objects.create(
            sender=content.author,
            recipient=reviewer,
            notification_type="content_approval_request",
            content=content,
            title=_("New Content Approval Request"),
            message=_('Student {student_name} has created a new post "{title}" that requires your approval.').format(
                student_name=content.author.get_full_name() or getattr(content.author, "username", ""),
                title=getattr(content, "title", ""),
            ),
            status="pending",
        )

        try:
            send_notification_to_user(reviewer, notification)
        except Exception:
            pass

        notifications.append(notification)

    return notifications


def create_content_approved_notification(content, approved_by) -> Notification:
    """
    Notify student that content has been approved.
    """

    notification = Notification.objects.create(
        sender=approved_by,
        recipient=content.author,
        notification_type="content_approved",
        content=content,
        title=_("Content Approved"),
        message=_('Your post "{title}" has been approved and is now visible to the community.').format(
            title=getattr(content, "title", ""),
        ),
        status="accepted",
    )

    try:
        send_notification_to_user(content.author, notification)
    except Exception:
        pass

    return notification


def create_content_rejected_notification(content, rejected_by, rejection_reason: str = "") -> Notification:
    """
    Notify student that content has been rejected.
    """

    message = _('Your post "{title}" has been rejected.').format(title=getattr(content, "title", ""))
    if rejection_reason:
        message += f" {_('Reason')}: {rejection_reason}"

    notification = Notification.objects.create(
        sender=rejected_by,
        recipient=content.author,
        notification_type="content_rejected",
        content=content,
        title=_("Content Rejected"),
        message=message,
        status="rejected",
        response_message=rejection_reason or None,
    )

    try:
        send_notification_to_user(content.author, notification)
    except Exception:
        pass

    return notification
