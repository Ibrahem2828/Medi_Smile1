# apps/appointments/services.py
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from apps.audit.services import log_audit_event
from apps.accounts.models import Role
from .models import Appointment


def create_appointment(*, student, case, data: dict) -> Appointment:
    if student.role.name != Role.STUDENT:
        raise PermissionDenied

    appointment = Appointment.objects.create(
        case=case,
        student=student,
        scheduled_at=data["scheduled_at"],
        notes=data.get("notes", ""),
    )

    log_audit_event(
        user=student,
        university=case.university,
        action="appointments.appointment.created",
        description="Student created appointment",
        content_object=appointment,
        metadata={"case_id": str(case.id)},
    )

    return appointment


def update_appointment(*, student, appointment: Appointment, data: dict):
    if student.role.name != Role.STUDENT:
        raise PermissionDenied

    appointment.scheduled_at = data.get("scheduled_at", appointment.scheduled_at)
    appointment.notes = data.get("notes", appointment.notes)
    appointment.save()

    log_audit_event(
        user=student,
        university=appointment.case.university,
        action="appointments.appointment.updated",
        description="Student updated appointment",
        content_object=appointment,
    )

    return appointment


def complete_appointment(*, student, appointment: Appointment):
    if student.role.name != Role.STUDENT:
        raise PermissionDenied

    appointment.completed_at = timezone.now()
    appointment.is_completed = True
    appointment.save()

    log_audit_event(
        user=student,
        university=appointment.case.university,
        action="appointments.appointment.completed",
        description="Appointment completed",
        content_object=appointment,
    )

    return appointment
