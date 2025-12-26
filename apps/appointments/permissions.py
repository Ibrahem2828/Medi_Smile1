# apps/appointments/permissions.py
from rest_framework.permissions import BasePermission

from apps.accounts.models import Role
from .models import Appointment


# ============================================================
# Helpers
# ============================================================
def is_patient(user, appointment: Appointment) -> bool:
    return appointment.patient_id == user.id


def is_student(user, appointment: Appointment) -> bool:
    return appointment.student_id == user.id


def is_supervisor(user, appointment: Appointment) -> bool:
    return appointment.supervisor_id == user.id


def is_university_admin(user, appointment: Appointment) -> bool:
    try:
        profile = user.universityadminprofile_profile
    except Exception:
        return False
    return appointment.case.university_id == profile.university_id


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
# Appointment Permissions
# ============================================================
class CanViewAppointment(BasePermission):
    """
    Read access:
    - Patient: own appointments
    - Student: assigned appointments
    - Supervisor: supervised appointments
    - University Admin: university scope (read-only)
    - IT Support: full read
    """

    def has_object_permission(self, request, view, obj: Appointment):
        user = request.user
        role = user.role.name

        if role == Role.TECH_SUPPORT:
            return True

        if role == Role.PATIENT:
            return is_patient(user, obj)

        if role == Role.STUDENT:
            return is_student(user, obj)

        if role == Role.SUPERVISOR:
            return is_supervisor(user, obj)

        if role == Role.UNIVERSITY_ADMIN:
            return is_university_admin(user, obj)

        return False


class CanCreateAppointment(BasePermission):
    """
    Create:
    - Student: for assigned case
    - Supervisor: for supervised case (exception)
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role.name in {Role.STUDENT, Role.SUPERVISOR}
        )


class CanUpdateAppointment(BasePermission):
    """
    Update:
    - Patient: ❌
    - Student: own appointment
    - Supervisor: own appointment (status only, validated in serializer)
    - University Admin / IT: ❌ (medical integrity)
    """

    def has_object_permission(self, request, view, obj: Appointment):
        user = request.user
        role = user.role.name

        if role == Role.STUDENT:
            return is_student(user, obj)

        if role == Role.SUPERVISOR:
            return is_supervisor(user, obj)

        return False
