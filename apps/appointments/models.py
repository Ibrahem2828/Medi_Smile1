# apps/appointments/models.py

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.cases.models import Case


class Appointment(models.Model):
    """
    Appointment model.

    Represents a scheduled clinical appointment within a dental case.
    - Created ONLY by student (or supervisor in special cases)
    - Patient cannot create or edit appointments
    - Used to organize treatment sessions (CaseSession)
    """

    # ============================================================
    # Status
    # ============================================================

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Scheduled")
        CONFIRMED = "confirmed", _("Confirmed")
        IN_PROGRESS = "in_progress", _("In Progress")
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

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="patient_appointments",
        limit_choices_to={"role": "patient"},
        verbose_name=_("Patient"),
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="student_appointments",
        limit_choices_to={"role": "student"},
        verbose_name=_("Student"),
        help_text=_("Student responsible for this appointment."),
    )

    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_appointments",
        limit_choices_to={"role": "supervisor"},
        verbose_name=_("Supervisor"),
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_appointments",
        limit_choices_to={"role__in": ["student", "supervisor"]},
        verbose_name=_("Created By"),
        help_text=_("User who created the appointment."),
    )

    # ============================================================
    # Appointment Details
    # ============================================================

    appointment_date = models.DateTimeField(
        verbose_name=_("Appointment Date"),
        help_text=_("Scheduled date and time for the appointment."),
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

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    # ============================================================
    # Meta
    # ============================================================

    class Meta:
        db_table = "appointments"
        verbose_name = _("Appointment")
        verbose_name_plural = _("Appointments")
        ordering = ["-appointment_date"]
        indexes = [
            models.Index(fields=["appointment_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["student"]),
            models.Index(fields=["patient"]),
        ]

    # ============================================================
    # Business Rules
    # ============================================================

    def clean(self):
        """
        Enforce MediSmile business rules.
        """

        # Case consistency
        if self.case.patient != self.patient:
            raise ValidationError(_("Patient must match the case patient."))

        if self.case.student != self.student:
            raise ValidationError(_("Student must be assigned to the case."))

        if self.supervisor and self.case.supervisor != self.supervisor:
            raise ValidationError(_("Supervisor must match the case supervisor."))

        # Appointment immutability after completion
        if self.pk:
            old_status = (
                Appointment.objects
                .filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

            if old_status in {self.Status.COMPLETED, self.Status.CANCELLED}:
                raise ValidationError(_("Completed or cancelled appointments cannot be modified."))

    # ============================================================
    # String
    # ============================================================

    def __str__(self):
        return (
            f"Appointment | {self.appointment_date:%Y-%m-%d %H:%M} "
            f"| Patient: {self.patient.email}"
        )
