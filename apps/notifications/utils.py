# apps/notifications/utils.py
from typing import Iterable

from apps.accounts.models import User, Role
from apps.appointments.models import Appointment
from apps.cases.models import Case
from apps.messaging.models import Room


def get_users_for_appointment_notifications(
    appointment: Appointment,
) -> Iterable[User]:
    """
    Resolve all users related to an appointment.
    """
    users = []
    if appointment.patient_id:
        users.append(appointment.patient)
    if appointment.student_id:
        users.append(appointment.student)
    if appointment.supervisor_id:
        users.append(appointment.supervisor)
    return users


def get_users_for_case_notifications(case: Case) -> Iterable[User]:
    """
    Resolve all users related to a case.
    """
    users = []
    if case.patient_id:
        users.append(case.patient)
    if case.student_id:
        users.append(case.student)
    if case.supervisor_id:
        users.append(case.supervisor)
    return users


def can_user_read_notification(user: User, notification) -> bool:
    """
    Centralized read permission logic for notifications.
    """
    role = user.role.name

    if role == Role.TECH_SUPPORT:
        return True

    if notification.recipient_id == user.id:
        return True

    # University Admin: read-only scoped
    if role == Role.UNIVERSITY_ADMIN:
        try:
            profile = user.universityadminprofile_profile
        except Exception:
            return False

        # Appointment-scoped
        if notification.appointment_id:
            return (
                notification.appointment.case.university_id
                == profile.university_id
            )

        # Case-scoped generic target
        if isinstance(notification.target_object, Case):
            return (
                notification.target_object.university_id
                == profile.university_id
            )

    return False
