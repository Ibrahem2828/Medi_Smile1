# apps/notifications/services.py
from __future__ import annotations

from typing import Optional
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.cases.models import Case
from apps.messaging.models import Message

from .models import Notification
from .utils import (
    get_users_for_appointment_notifications,
    get_users_for_case_notifications,
)


# ============================================================
# Core Factory (Single Source of Truth)
# ============================================================

def create_notification(
    *,
    sender: Optional[User],
    recipient: User,
    notification_type: str,
    title: str,
    message: str,
    priority: str = Notification.Priority.NORMAL,
    appointment: Optional[Appointment] = None,
    target_object=None,
    proposed_changes: Optional[dict] = None,
    payload: Optional[dict] = None,
) -> Notification:
    """
    Central notification creation entry-point.

    Notes:
    - `payload` is generic extra data (frontend-friendly).
    - `target_object` is linked via GenericFK (if your model supports it).
    - `proposed_changes` is used for appointment update requests.
    """
    notification = Notification(
        sender=sender,
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        proposed_changes=proposed_changes,
    )

    # Optional generic payload if exists in your model
    if hasattr(notification, "payload"):
        notification.payload = payload or {}

    if appointment:
        notification.appointment = appointment

    if target_object:
        notification.target_content_type = ContentType.objects.get_for_model(
            target_object.__class__
        )
        notification.target_object_id = target_object.id

    notification.save()
    return notification


# ============================================================
# Minimal Generic Helper (Used by audit bridge)
# ============================================================

def notify_user(
    *,
    recipient: User,
    title: str,
    message: str,
    notification_type: str = "system",
    sender: Optional[User] = None,
    target_object=None,
    payload: Optional[dict] = None,
    priority: str = Notification.Priority.NORMAL,
) -> Notification:
    """
    Lightweight wrapper for simple system notifications.
    Keeps the Notification model usage consistent.
    """
    return create_notification(
        sender=sender,
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        target_object=target_object,
        payload=payload,
    )


# ============================================================
# Appointment Notifications
# ============================================================

def notify_appointment_update_request(
    *,
    sender: User,
    appointment: Appointment,
    proposed_changes: dict,
):
    """
    Patient → Student / Supervisor
    """
    recipients = [
        u
        for u in get_users_for_appointment_notifications(appointment)
        if u and u.id != sender.id
    ]

    for recipient in recipients:
        create_notification(
            sender=sender,
            recipient=recipient,
            notification_type="appointment_update_request",
            title="Appointment Update Request",
            message="A request to update the appointment has been submitted.",
            appointment=appointment,
            proposed_changes=proposed_changes,
            payload={"appointment_id": str(appointment.id)},
        )


def notify_appointment_confirmed(
    *,
    sender: User,
    appointment: Appointment,
):
    """
    Student → Patient
    """
    create_notification(
        sender=sender,
        recipient=appointment.patient,
        notification_type="appointment_confirmed",
        title="Appointment Confirmed",
        message="Your appointment has been confirmed.",
        appointment=appointment,
        payload={"appointment_id": str(appointment.id)},
    )


# ============================================================
# Messaging Notifications
# ============================================================

def notify_new_message(
    *,
    message_obj: Message,
):
    """
    Triggered when a new chat message is sent.
    """
    room = message_obj.room
    sender = message_obj.sender

    recipients = [room.participant1, room.participant2]

    for user in recipients:
        if not user or user.id == sender.id:
            continue

        create_notification(
            sender=sender,
            recipient=user,
            notification_type="new_message",
            title="New Message",
            message="You have received a new message.",
            target_object=room.case,
            payload={
                "room_id": str(room.id),
                "case_id": str(room.case_id),
            },
        )


# ============================================================
# Case Notifications
# ============================================================

def notify_case_assigned(
    *,
    sender: User,
    case: Case,
):
    """
    University / Supervisor → Student
    """
    if not case.student:
        return

    create_notification(
        sender=sender,
        recipient=case.student,
        notification_type="case_assigned",
        title="New Case Assigned",
        message="A new case has been assigned to you.",
        target_object=case,
        payload={"case_id": str(case.id)},
    )


def notify_case_update(
    *,
    sender: User,
    case: Case,
    title: str,
    message: str,
):
    """
    Notify related users in the case scope (patient, student, supervisor) except sender.
    """
    recipients = [
        u for u in get_users_for_case_notifications(case)
        if u and u.id != sender.id
    ]

    for recipient in recipients:
        create_notification(
            sender=sender,
            recipient=recipient,
            notification_type="case_update",
            title=title,
            message=message,
            target_object=case,
            payload={"case_id": str(case.id)},
        )
