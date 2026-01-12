# apps/messaging/permissions.py
from rest_framework.permissions import BasePermission

from apps.accounts.models import Role
from apps.cases.models import Case
from apps.universities.models import Course
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


def is_course_participant(user, course: Course) -> bool:
    if user == course.supervisor:
        return True
    return course.students.filter(id=user.id).exists()


def is_university_admin_for_case(user, case: Case) -> bool:
    """
    University Admin can read data scoped to their university only.
    """
    try:
        profile = user.universityadminprofile_profile
    except Exception:
        return False
    return bool(profile.university_id) and profile.university_id == case.university_id


def is_university_admin_for_room(user, room: Room) -> bool:
    try:
        profile = user.universityadminprofile_profile
    except Exception:
        return False
    university_id = None
    if room.case_id:
        university_id = room.case.university_id
    elif room.course_id:
        university_id = room.course.university_id
    return bool(profile.university_id) and profile.university_id == university_id


def is_case_chat_open(case: Case) -> bool:
    """
    State guard: chat is allowed only while the case is active with an assigned student.
    """
    return case.status in {
        Case.Status.ASSIGNED,
        Case.Status.IN_PROGRESS,
    }


def is_course_chat_open(course: Course) -> bool:
    return bool(course.is_active)


def is_room_chat_open(room_or_case_or_course) -> bool:
    if room_or_case_or_course is None:
        return True
    if isinstance(room_or_case_or_course, Room):
        if room_or_case_or_course.thread_type == Room.ThreadType.COURSE:
            if not room_or_case_or_course.course_id:
                return False
            return is_course_chat_open(room_or_case_or_course.course)
        if not room_or_case_or_course.case_id:
            return False
        return is_case_chat_open(room_or_case_or_course.case)
    if isinstance(room_or_case_or_course, Course):
        return is_course_chat_open(room_or_case_or_course)
    return is_case_chat_open(room_or_case_or_course)


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
    - Case thread: patient / student / supervisor of the case
    - Course thread: student / supervisor participants
    - University Admin (read-only, scoped)
    - IT Support (global)
    """

    def has_object_permission(self, request, view, obj: Room):
        user = request.user
        role = getattr(user, "role_name", None) or getattr(getattr(user, "role", None), "name", None)
        case = obj.case

        if role == Role.TECH_SUPPORT:
            return True

        if obj.thread_type == Room.ThreadType.COURSE:
            if role in {Role.STUDENT, Role.SUPERVISOR}:
                return user in {obj.participant_student, obj.participant_supervisor}
            if role == Role.UNIVERSITY_ADMIN:
                return is_university_admin_for_room(user, obj)
            return False

        if role in [Role.PATIENT, Role.STUDENT, Role.SUPERVISOR]:
            return is_case_participant(user, case)

        if role == Role.UNIVERSITY_ADMIN:
            return is_university_admin_for_case(user, case)

        return False


class CanCreateRoom(BasePermission):
    """
    CREATE Room:
    - Automatically handled (1 room per case / course pair)
    - Only thread participants can trigger access
    """

    def has_permission(self, request, view):
        role = getattr(request.user, "role_name", None)
        return role in {Role.PATIENT, Role.STUDENT, Role.SUPERVISOR}


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
        if not is_room_chat_open(obj):
            return False

        if obj.thread_type == Room.ThreadType.COURSE:
            if role not in {Role.STUDENT, Role.SUPERVISOR}:
                return False
            return user in {obj.participant_student, obj.participant_supervisor}

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

        if room.thread_type == Room.ThreadType.COURSE:
            if role in {Role.STUDENT, Role.SUPERVISOR}:
                return user in {room.participant_student, room.participant_supervisor}
            if role == Role.UNIVERSITY_ADMIN:
                return is_university_admin_for_room(user, room)
            return False

        if role in [Role.PATIENT, Role.STUDENT, Role.SUPERVISOR]:
            return is_case_participant(user, case)

        if role == Role.UNIVERSITY_ADMIN:
            return is_university_admin_for_case(user, case)

        return False
