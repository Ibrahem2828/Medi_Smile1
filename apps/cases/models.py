import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.universities.models import University


# ============================================================
# Case (Core Medical Entity)
# ============================================================

class Case(models.Model):
    """
    Dental medical case.

    Represents ONE dental problem for ONE patient.
    A patient can have ONLY ONE active case at a time.
    """

    # --------------------------------------------------------
    # Status & Priority
    # --------------------------------------------------------

    class Status(models.TextChoices):
        NEW = "new", _("New (Initial Diagnosis)")
        PENDING_ASSIGNMENT = "pending_assignment", _("Pending Assignment")
        ASSIGNED = "assigned", _("Assigned to Student")
        IN_PROGRESS = "in_progress", _("In Progress")
        COMPLETED = "completed", _("Completed")
        CLOSED = "closed", _("Closed (Finalized)")

    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        URGENT = "urgent", _("Urgent")

    ACTIVE_STATUSES = {
        Status.NEW,
        Status.PENDING_ASSIGNMENT,
        Status.ASSIGNED,
        Status.IN_PROGRESS,
    }

    ALLOWED_TRANSITIONS = {
        Status.NEW: {Status.PENDING_ASSIGNMENT},
        Status.PENDING_ASSIGNMENT: {Status.ASSIGNED},
        Status.ASSIGNED: {Status.IN_PROGRESS},
        Status.IN_PROGRESS: {Status.COMPLETED},
        Status.COMPLETED: {Status.CLOSED},
    }

    # --------------------------------------------------------
    # Fields
    # --------------------------------------------------------

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=200, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))

    # --------------------------------------------------------
    # Relations
    # --------------------------------------------------------

    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name="cases",
        verbose_name=_("University"),
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="patient_cases",
        limit_choices_to={"role": "patient"},
        verbose_name=_("Patient"),
    )

    student = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_cases",
        limit_choices_to={"role": "student"},
        verbose_name=_("Assigned Student"),
    )

    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_cases",
        limit_choices_to={"role": "supervisor"},
        verbose_name=_("Supervisor"),
    )

    # --------------------------------------------------------
    # State & Visibility
    # --------------------------------------------------------

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name=_("Status"),
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name=_("Priority"),
    )

    is_public = models.BooleanField(
        default=False,
        verbose_name=_("Visible for Assignment"),
        help_text=_("If true, students can request assignment."),
    )

    # --------------------------------------------------------
    # Timestamps
    # --------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    # --------------------------------------------------------
    # Meta
    # --------------------------------------------------------

    class Meta:
        db_table = "cases"
        verbose_name = _("Case")
        verbose_name_plural = _("Cases")
        ordering = ["-created_at"]

    # --------------------------------------------------------
    # Business Rules
    # --------------------------------------------------------

    def clean(self):
        # Patient role validation
        if self.patient.role != "patient":
            raise ValidationError(_("Assigned patient must have role 'patient'."))

        # Single active case per patient
        if self.status in self.ACTIVE_STATUSES:
            qs = Case.objects.filter(
                patient=self.patient,
                status__in=self.ACTIVE_STATUSES,
            ).exclude(id=self.id)

            if qs.exists():
                raise ValidationError(_("This patient already has an active case."))

        # Status transition validation
        if self.pk:
            previous_status = (
                Case.objects
                .filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

            if previous_status == self.Status.CLOSED:
                raise ValidationError(_("Closed cases cannot be modified."))

            if previous_status and previous_status != self.status:
                allowed = self.ALLOWED_TRANSITIONS.get(previous_status, set())
                if self.status not in allowed:
                    raise ValidationError(_("Invalid case status transition."))

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


# ============================================================
# Case History (Immutable Audit Trail)
# ============================================================

class CaseHistory(models.Model):
    """
    Immutable legal and educational audit trail for a case.
    """

    class Action(models.TextChoices):
        CREATED = "created", _("Created")
        ASSIGNMENT_REQUESTED = "assignment_requested", _("Assignment Requested")
        ASSIGNED = "assigned", _("Assigned")
        STATUS_CHANGED = "status_changed", _("Status Changed")
        SESSION_CREATED = "session_created", _("Session Created")
        SESSION_REVIEWED = "session_reviewed", _("Session Reviewed")
        COMPLETED = "completed", _("Completed")
        CLOSED = "closed", _("Closed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name=_("Case"),
    )

    action = models.CharField(
        max_length=50,
        choices=Action.choices,
        verbose_name=_("Action"),
    )

    description = models.TextField(verbose_name=_("Description"))

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Performed By"),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        db_table = "case_history"
        verbose_name = _("Case History")
        verbose_name_plural = _("Case Histories")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(_("Case history records are immutable."))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.case.id} - {self.get_action_display()}"


# ============================================================
# Case Assignment Request
# ============================================================

class CaseAssignmentRequest(models.Model):
    """
    Student request to take ownership of a public case.
    Approved ONLY by supervisor.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACCEPTED = "accepted", _("Accepted")
        REJECTED = "rejected", _("Rejected")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="assignment_requests",
        verbose_name=_("Case"),
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="case_assignment_requests",
        limit_choices_to={"role": "student"},
        verbose_name=_("Student"),
    )

    message = models.TextField(blank=True, null=True, verbose_name=_("Student Message"))

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status"),
    )

    supervisor_response = models.TextField(
        blank=True, null=True, verbose_name=_("Supervisor Response")
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = "case_assignment_requests"
        verbose_name = _("Case Assignment Request")
        verbose_name_plural = _("Case Assignment Requests")
        ordering = ["-created_at"]
        unique_together = ["case", "student"]

    def clean(self):
        if self.student.role != "student":
            raise ValidationError(_("Only students can request case assignment."))

        if not self.case.is_public:
            raise ValidationError(_("This case is not open for assignment."))

        if self.case.status != Case.Status.PENDING_ASSIGNMENT:
            raise ValidationError(_("Case is not accepting assignment requests."))

    def __str__(self):
        return f"{self.case.id} - {self.student.email}"


# ============================================================
# Case Session (Treatment Session)
# ============================================================

class CaseSession(models.Model):
    """
    A single treatment session within a case.

    Created by student.
    Reviewed and approved by supervisor.
    Read-only for patient.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        COMPLETED = "completed", _("Completed by Student")
        NEEDS_REVIEW = "needs_review", _("Needs Supervisor Review")
        APPROVED = "approved", _("Approved by Supervisor")
        REJECTED = "rejected", _("Rejected by Supervisor")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name=_("Case"),
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="case_sessions",
        limit_choices_to={"role": "student"},
        verbose_name=_("Student"),
    )

    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_sessions",
        limit_choices_to={"role": "supervisor"},
        verbose_name=_("Supervisor"),
    )

    notes = models.TextField(
        verbose_name=_("Clinical Notes"),
        help_text=_("Written by the student after the session."),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Session Status"),
    )

    supervisor_feedback = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Supervisor Feedback"),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = "case_sessions"
        verbose_name = _("Case Session")
        verbose_name_plural = _("Case Sessions")
        ordering = ["created_at"]

    def clean(self):
        if self.student.role != "student":
            raise ValidationError(_("Session creator must be a student."))

        if self.case.student != self.student:
            raise ValidationError(_("Student is not assigned to this case."))

        if self.case.status not in {
            Case.Status.ASSIGNED,
            Case.Status.IN_PROGRESS,
        }:
            raise ValidationError(_("Sessions can only be created for active cases."))

    def __str__(self):
        return f"Session {self.id} - {self.case.id}"
