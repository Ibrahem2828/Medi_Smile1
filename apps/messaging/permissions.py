# apps/messaging/permissions.py
from rest_framework.permissions import BasePermission

from apps.accounts.models import Role
from apps.cases.models import Case
from .models import Room, Message


# ============================================================
# Helpers
# ============================================================
def is_case_participant(user, case: Case) -> bool:
    """
    Ownership check:
    - Patient assigned to the case
    - Student assigned to the case
    - Supervisor of the case (read only)
    """
    return user in {case.patient, case.student, case.supervisor}


def is_university_admin_for_case(user, case: Case) -> bool:
    """
    University Admin can read data scoped to their university only.
    """
    try:
        profile = user.universityadminprofile_profile
    except Exception:
        return False
    return bool(profile.university_id) and profile.university_id == case.university_id


def is_case_chat_open(case: Case) -> bool:
    """
    State guard: chat is allowed only while the case is active with an assigned student.
    """
    return case.status in {
        Case.Status.ASSIGNED,
        Case.Status.IN_PROGRESS,
    }


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
        role = getattr(user, "role_name", None) or getattr(getattr(user, "role", None), "name", None)
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
        role = getattr(request.user, "role_name", None)
        return role in {Role.PATIENT, Role.STUDENT}


# ============================================================
# Message Permissions
# ============================================================
class CanSendMessage(BasePermission):
    """
    SEND message:
    - Only patient or assigned student while case is active
    """

    def has_object_permission(self, request, view, obj: Room):
        user = request.user
        role = getattr(user, "role_name", None) or getattr(getattr(user, "role", None), "name", None)
        case = obj.case

        if not is_case_chat_open(case):
            return False

        if role not in {Role.PATIENT, Role.STUDENT}:
            return False

        return user in {obj.participant_patient, obj.participant_student}


class CanViewMessage(BasePermission):
    """
    READ messages:
    - Room participants
    - University Admin (read-only)
    - IT Support
    """

    def has_object_permission(self, request, view, obj: Message):
        user = request.user
        role = getattr(user, "role_name", None) or getattr(getattr(user, "role", None), "name", None)
        room = obj.room
        case = room.case

        if role == Role.TECH_SUPPORT:
            return True

        if role in [Role.PATIENT, Role.STUDENT, Role.SUPERVISOR]:
            return is_case_participant(user, case)

        if role == Role.UNIVERSITY_ADMIN:
            return is_university_admin_for_case(user, case)

        return False
