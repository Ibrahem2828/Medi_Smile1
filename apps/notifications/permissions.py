# apps/notifications/permissions.py
from rest_framework.permissions import BasePermission

from apps.accounts.models import Role
from .models import Notification


def is_notification_recipient(user, obj: Notification) -> bool:
    return obj.recipient_id == getattr(user, "id", None)


def is_same_university(user, obj: Notification) -> bool:
    """
    University scope: only admin of the same university or recipient themselves.
    """
    # Recipient check
    if obj.recipient_id == getattr(user, "id", None):
        return True

    if getattr(user, "role_name", None) != Role.UNIVERSITY_ADMIN:
        return False

    # Try resolving university from recipient profile
    try:
        recipient_profile = obj.recipient.universityadminprofile_profile
    except Exception:
        recipient_profile = None

    try:
        user_profile = user.universityadminprofile_profile
    except Exception:
        user_profile = None

    if not recipient_profile or not user_profile:
        return False

    return recipient_profile.university_id == user_profile.university_id


class IsRecipient(BasePermission):
    def has_object_permission(self, request, view, obj: Notification):
        return is_notification_recipient(request.user, obj)
