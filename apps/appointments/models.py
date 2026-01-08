# apps/appointments/models.py
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role
from apps.cases.models import Case


class Appointment(models.Model):
    """
    Appointment model.

    Represents a scheduled clinical appointment within a dental case.
    Rules (per MediSmile):
    - Created by: Student (default) OR Supervisor (exceptional)
    - Patient: read-only (cannot create/update date)
    - Student: controls scheduling + rescheduling + most status actions
    - Supervisor: limited updates (mainly status oversight)
    """

    # ============================================================
    # Status
    # ============================================================
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Scheduled")
        RESCHEDULED = "rescheduled", _("Rescheduled")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")
        NO_SHOW = "no_show", _("No Show")

    # ============================================================
    # Core Fields
    # ============================================================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="appointments",
        verbose_name=_("Related Case"),
        help_text=_("Dental case this appointment belongs to."),
    )

    # denormalized references for fast access / reporting
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="patient_appointments",
        limit_choices_to={"role__name": Role.PATIENT},
        verbose_name=_("Patient"),
    )

    student = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_appointments",
        limit_choices_to={"role__name": Role.STUDENT},
        verbose_name=_("Student"),
        help_text=_("Student responsible for this appointment (nullable before assignment)."),
    )

    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_appointments",
        limit_choices_to={"role__name": Role.SUPERVISOR},
        verbose_name=_("Supervisor"),
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_appointments",
        limit_choices_to={"role__name__in": [Role.STUDENT, Role.SUPERVISOR]},
        verbose_name=_("Created By"),
        help_text=_("User who created the appointment."),
    )

    # ============================================================
    # Appointment Details
    # ============================================================
    scheduled_at = models.DateTimeField(
        verbose_name=_("Scheduled At"),
        help_text=_("Scheduled date and time for the appointment."),
    )

    duration_minutes = models.PositiveSmallIntegerField(
        default=30,
        verbose_name=_("Duration (minutes)"),
        help_text=_("Expected duration of the appointment."),
    )

    location = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Location"),
        help_text=_("Physical location if in-person."),
    )

    telehealth_link = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("Telehealth Link"),
        help_text=_("Virtual meeting link if remote."),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        verbose_name=_("Status"),
    )

    is_follow_up = models.BooleanField(
        default=False,
        verbose_name=_("Follow-up Appointment"),
        help_text=_("Indicates if this appointment is a follow-up."),
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Internal Notes"),
        help_text=_("Optional notes by student or supervisor."),
    )

    is_archived = models.BooleanField(
        default=False,
        verbose_name=_("Archived"),
        help_text=_("Soft-hide old appointments without deletion."),
    )

    # ============================================================
    # Audit
    # ============================================================
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    # ============================================================
    # Meta
    # ============================================================
    class Meta:
        db_table = "appointments"
        verbose_name = _("Appointment")
        verbose_name_plural = _("Appointments")
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["scheduled_at"], name="idx_appt_date"),
            models.Index(fields=["status"], name="idx_appt_status"),
            models.Index(fields=["student"], name="idx_appt_student"),
            models.Index(fields=["patient"], name="idx_appt_patient"),
            models.Index(fields=["case"], name="idx_appt_case"),
            models.Index(fields=["is_archived"], name="idx_appt_archived"),
        ]

    # ============================================================
    # Business Rules
    # ============================================================
    def clean(self):
        """
        Enforce MediSmile business rules:
        - Appointment must match the case participants
        - Appointment must align with case lifecycle
        - Immutable once completed/cancelled/no_show
        """

        super().clean()

        # Case status eligibility
        if self.case.status not in {Case.Status.ACCEPTED, Case.Status.ASSIGNED, Case.Status.IN_PROGRESS}:
            raise ValidationError(_("Appointment cannot be created for this case status."))

        # Consistency with case participants
        if self.case.patient_id != self.patient_id:
            raise ValidationError(_("Patient must match the case patient."))

        if self.case.student_id:
            if self.student_id and self.case.student_id != self.student_id:
                raise ValidationError(_("Student must match the assigned case student."))
        else:
            # If case has no student yet, appointment can omit student (supervisor-created)
            if self.student_id:
                raise ValidationError(_("Student cannot be set before case assignment."))

        if self.case.supervisor_id:
            # If case has a supervisor, appointment supervisor must match it (or be empty and auto-filled by logic)
            if self.supervisor_id and self.case.supervisor_id != self.supervisor_id:
                raise ValidationError(_("Supervisor must match the case supervisor."))
        else:
            # If case has no supervisor yet, appointment should not set one
            if self.supervisor_id:
                raise ValidationError(_("Cannot set supervisor before the case has a supervisor."))

        # created_by must be student or supervisor
        role_name = getattr(self.created_by.role, "name", None) if self.created_by_id else None
        if role_name not in {Role.STUDENT, Role.SUPERVISOR}:
            raise ValidationError(_("Only student or supervisor can create an appointment."))

        # Immutability once final
        if self.pk:
            old_status = (
                Appointment.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )
            if old_status in {self.Status.COMPLETED, self.Status.CANCELLED, self.Status.NO_SHOW}:
                raise ValidationError(_("Completed/cancelled/no-show appointments cannot be modified."))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Appointment | {self.scheduled_at:%Y-%m-%d %H:%M} | Patient: {self.patient.email}"
