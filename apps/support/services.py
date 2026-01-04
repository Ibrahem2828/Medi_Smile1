# apps/support/services.py
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import Role, User
from apps.audit.services import log_audit_event
from apps.notifications.models import Notification
from .models import SupportTicket, SupportTicketResponse


# ============================================================
# Ticket Services
# ============================================================

def create_support_ticket(*, user, data: dict) -> SupportTicket:
    """
    Create a support ticket for any authenticated user.
    """
    ticket = SupportTicket.objects.create(
        created_by=user,
        **data,
    )

    log_audit_event(
        user=user,
        action="support.ticket.created",
        description="Support ticket created",
        content_object=ticket,
        metadata={
            "priority": ticket.priority,
            "status": ticket.status,
        },
    )

    # Notify tech support team about new ticket
    tech_support_users = User.objects.filter(role__name=Role.TECH_SUPPORT)
    _notify(ticket, sender=user, recipients=tech_support_users, notif_type="system_alert", title="تذكرة دعم جديدة", message=f"تذكرة دعم من {user.email} ذات أولوية {ticket.priority}")

    return ticket


def update_support_ticket(*, user, ticket: SupportTicket, data: dict) -> SupportTicket:
    """
    Update ticket status / priority / assignment.
    """

    role_name = user.role.name

    if role_name not in {Role.TECH_SUPPORT, Role.UNIVERSITY_ADMIN}:
        raise PermissionDenied("You are not allowed to update this ticket.")

    # University admin restrictions
    if role_name == Role.UNIVERSITY_ADMIN:
        forbidden_fields = {"assigned_to", "resolution"}
        if forbidden_fields & set(data.keys()):
            raise PermissionDenied("University admin has limited update permissions.")

    old_status = ticket.status
    new_status = data.get("status")

    if new_status == SupportTicket.Status.RESOLVED:
        if not (data.get("resolution") or ticket.resolution):
            raise PermissionDenied("Resolved tickets must include a resolution.")
        ticket.resolved_at = ticket.resolved_at or timezone.now()

    if new_status == SupportTicket.Status.CLOSED:
        ticket.closed_at = ticket.closed_at or timezone.now()
        if not ticket.resolved_at and (data.get("resolution") or ticket.resolution):
            ticket.resolved_at = timezone.now()

    for field, value in data.items():
        setattr(ticket, field, value)

    ticket.save()

    log_audit_event(
        user=user,
        action="support.ticket.updated",
        description="Support ticket updated",
        content_object=ticket,
        metadata={
            "old_status": old_status,
            "new_status": ticket.status,
        },
    )

    return ticket


# ============================================================
# Response Services
# ============================================================

def add_ticket_response(
    *,
    ticket: SupportTicket,
    user,
    message: str,
    is_internal: bool = False,
) -> SupportTicketResponse:
    """
    Add response to ticket.
    """

    role_name = user.role.name

    if is_internal and role_name != Role.TECH_SUPPORT:
        raise PermissionDenied("Internal notes are restricted to tech support.")

    # Auto move ticket to IN_PROGRESS when tech replies
    if role_name == Role.TECH_SUPPORT and ticket.status == SupportTicket.Status.OPEN:
        ticket.status = SupportTicket.Status.IN_PROGRESS
        ticket.save(update_fields=["status", "updated_at"])

    response = SupportTicketResponse.objects.create(
        ticket=ticket,
        author=user,
        message=message,
        is_internal=is_internal,
    )

    log_audit_event(
        user=user,
        action="support.ticket.replied",
        description="Support ticket replied",
        content_object=ticket,
        metadata={
            "is_internal": is_internal,
        },
    )

    # Notify counterparty
    _notify_ticket_response(ticket=ticket, author=user, is_internal=is_internal)

    return response


# ============================================================
# Notification helpers
# ============================================================

def _notify(ticket: SupportTicket, sender, recipients, notif_type, title, message):
    if not recipients:
        return
    ct = ContentType.objects.get_for_model(ticket)
    Notification.objects.bulk_create(
        [
            Notification(
                sender=sender,
                recipient=recipient,
                notification_type=notif_type,
                priority=Notification.Priority.HIGH if ticket.priority == SupportTicket.Priority.URGENT else Notification.Priority.NORMAL,
                title=title,
                message=message,
                target_content_type=ct,
                target_object_id=ticket.id,
                payload={
                    "ticket_id": str(ticket.id),
                    "priority": ticket.priority,
                    "status": ticket.status,
                },
            )
            for recipient in recipients
        ]
    )


def _notify_ticket_response(*, ticket: SupportTicket, author, is_internal: bool):
    """
    Notify the other party:
    - If tech replies: notify ticket owner.
    - If owner replies: notify assigned tech support (or all tech support).
    - Skip internal notes for non-tech.
    """
    role_name = getattr(getattr(author, "role", None), "name", None)
    if is_internal:
        return

    if role_name == Role.TECH_SUPPORT:
        recipients = [ticket.created_by]
        notif_type = "system_alert"
        title = "رد من الدعم الفني"
        message = f"تم الرد على تذكرتك: {ticket.subject}"
    else:
        # notify assigned tech support or all tech support
        if ticket.assigned_to_id:
            recipients = [ticket.assigned_to]
        else:
            recipients = User.objects.filter(role__name=Role.TECH_SUPPORT)
        notif_type = "system_alert"
        title = "رد جديد على تذكرة دعم"
        message = f"هناك رد جديد على التذكرة: {ticket.subject}"

    _notify(ticket, sender=author, recipients=recipients, notif_type=notif_type, title=title, message=message)
