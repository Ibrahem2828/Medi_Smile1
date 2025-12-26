# apps/messaging/permissions.py
from rest_framework.permissions import BasePermission

from apps.accounts.models import Role
from apps.cases.models import Case
from .models import Room, Message


# ============================================================
# Helpers
# ============================================================
def is_case_participant(user, case: Case) -> bool:
    return user in [case.patient, case.student, case.supervisor]


def is_university_admin_for_case(user, case: Case) -> bool:
    try:
        profile = user.universityadminprofile_profile
    except Exception:
        return False
    return case.university_id == profile.university_id


# ============================================================
# Base
# ============================================================
class IsAuthenticatedAndActive(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )


# ============================================================
# Room Permissions
# ============================================================
class CanViewRoom(BasePermission):
    """
    READ Room:
    - Patient / Student / Supervisor of the case
    - University Admin (read-only, scoped)
    - IT Support (global)
    """

    def has_object_permission(self, request, view, obj: Room):
        user = request.user
        role = user.role.name
        case = obj.case

        if role == Role.TECH_SUPPORT:
            return True

        if role in [Role.PATIENT, Role.STUDENT, Role.SUPERVISOR]:
            return is_case_participant(user, case)

        if role == Role.UNIVERSITY_ADMIN:
            return is_university_admin_for_case(user, case)

        return False


class CanCreateRoom(BasePermission):
    """
    CREATE Room:
    - Automatically handled (1 room per case)
    - Only case participants can trigger access
    """

    def has_permission(self, request, view):
        return request.user.role.name in [
            Role.PATIENT,
            Role.STUDENT,
            Role.SUPERVISOR,
        ]


# ============================================================
# Message Permissions
# ============================================================
class CanSendMessage(BasePermission):
    """
    SEND message:
    - Only participants of the room
    """

    def has_object_permission(self, request, view, obj: Room):
        return request.user in [obj.participant1, obj.participant2]


class CanViewMessage(BasePermission):
    """
    READ messages:
    - Room participants
    - University Admin (read-only)
    - IT Support
    """

    def has_object_permission(self, request, view, obj: Message):
        user = request.user
        role = user.role.name
        room = obj.room
        case = room.case

        if role == Role.TECH_SUPPORT:
            return True

        if role in [Role.PATIENT, Role.STUDENT, Role.SUPERVISOR]:
            return user in [room.participant1, room.participant2]

        if role == Role.UNIVERSITY_ADMIN:
            return is_university_admin_for_case(user, case)

        return False
