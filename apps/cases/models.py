# apps/cases/models.py
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.accounts.models import User, Role
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
    # ✅ Optional until case is routed/assigned to a university
    university = models.ForeignKey(
        University,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases",
        verbose_name=_("University"),
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="patient_cases",
        limit_choices_to={"role__name": Role.PATIENT},
        verbose_name=_("Patient"),
    )

    student = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_cases",
        limit_choices_to={"role__name": Role.STUDENT},
        verbose_name=_("Assigned Student"),
    )

    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_cases",
        limit_choices_to={"role__name": Role.SUPERVISOR},
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

    class Meta:
        db_table = "cases"
        verbose_name = _("Case")
        verbose_name_plural = _("Cases")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="idx_case_status"),
            models.Index(fields=["priority"], name="idx_case_priority"),
            models.Index(fields=["created_at"], name="idx_case_created"),
            models.Index(fields=["is_public"], name="idx_case_public"),
            models.Index(fields=["university"], name="idx_case_university"),
            models.Index(fields=["patient"], name="idx_case_patient"),
            models.Index(fields=["student"], name="idx_case_student"),
            models.Index(fields=["supervisor"], name="idx_case_supervisor"),
        ]

    # --------------------------------------------------------
    # Business Rules
    # --------------------------------------------------------
    def clean(self):
        super().clean()

        # Role validation (FK-based)
        if self.patient and getattr(self.patient.role, "name", None) != Role.PATIENT:
            raise ValidationError(_("Assigned patient must have role 'patient'."))

        if self.student and getattr(self.student.role, "name", None) != Role.STUDENT:
            raise ValidationError(_("Assigned student must have role 'student'."))

        if self.supervisor and getattr(self.supervisor.role, "name", None) != Role.SUPERVISOR:
            raise ValidationError(_("Assigned supervisor must have role 'supervisor'."))

        # One active case per patient
        if self.patient and self.status in self.ACTIVE_STATUSES:
            qs = Case.objects.filter(
                patient=self.patient,
                status__in=self.ACTIVE_STATUSES,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError(_("This patient already has an active case."))

        # If case is public / pending assignment, university must be set
        if self.is_public or self.status == self.Status.PENDING_ASSIGNMENT:
            if not self.university_id:
                raise ValidationError(_("University is required for public/assignment cases."))

        # Status transition validation (immutable once closed)
        if self.pk:
            previous_status = (
                Case.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

            if previous_status == self.Status.CLOSED:
                raise ValidationError(_("Closed cases cannot be modified."))

            if previous_status and previous_status != self.status:
                allowed = self.ALLOWED_TRANSITIONS.get(previous_status, set())
                if self.status not in allowed:
                    raise ValidationError(_("Invalid case status transition."))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def latest_ai_diagnosis(self):
        from apps.ai.models import AIDiagnosis  # Local import to avoid circular dependency
        return getattr(self, "ai_diagnoses", AIDiagnosis.objects.none()).order_by("-created_at").first()

    @property
    def ai_status(self):
        latest = self.latest_ai_diagnosis
        return getattr(latest, "status", None)


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
        indexes = [
            models.Index(fields=["case", "created_at"], name="idx_casehistory_case_time"),
            models.Index(fields=["action"], name="idx_casehistory_action"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(_("Case history records are immutable."))
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.case_id} - {self.get_action_display()}"


# ============================================================
# Case Assignment Request
# ============================================================
class CaseAssignmentRequest(models.Model):
    """
    Student request to take ownership of a public case.
    Approved ONLY by supervisor (via services/views).
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
        limit_choices_to={"role__name": Role.STUDENT},
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
        constraints = [
            models.UniqueConstraint(fields=["case", "student"], name="uq_case_student_request"),
        ]
        indexes = [
            models.Index(fields=["case", "status"], name="idx_req_case_status"),
            models.Index(fields=["student", "status"], name="idx_req_student_status"),
        ]

    def clean(self):
        super().clean()

        if getattr(self.student.role, "name", None) != Role.STUDENT:
            raise ValidationError(_("Only students can request case assignment."))

        if not self.case.is_public:
            raise ValidationError(_("This case is not open for assignment."))

        if self.case.status != Case.Status.PENDING_ASSIGNMENT:
            raise ValidationError(_("Case is not accepting assignment requests."))

        if not self.case.university_id:
            raise ValidationError(_("Case must be linked to a university before assignment."))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.case_id} - {self.student.email}"


# ============================================================
# Case Session (Treatment Session)
# ============================================================
class CaseSession(models.Model):
    """
    A single treatment session within a case.
    Created by student.
    Reviewed by supervisor.
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
        limit_choices_to={"role__name": Role.STUDENT},
        verbose_name=_("Student"),
    )

    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_sessions",
        limit_choices_to={"role__name": Role.SUPERVISOR},
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
        indexes = [
            models.Index(fields=["case", "created_at"], name="idx_session_case_time"),
            models.Index(fields=["student", "created_at"], name="idx_session_student_time"),
            models.Index(fields=["status"], name="idx_session_status"),
        ]

    def clean(self):
        super().clean()

        if getattr(self.student.role, "name", None) != Role.STUDENT:
            raise ValidationError(_("Session creator must be a student."))

        if self.case.student_id != self.student_id:
            raise ValidationError(_("Student is not assigned to this case."))

        if self.case.status not in {Case.Status.ASSIGNED, Case.Status.IN_PROGRESS}:
            raise ValidationError(_("Sessions can only be created for active cases."))

        # Supervisor defaults to the case supervisor
        if self.case.supervisor_id and self.supervisor_id and self.supervisor_id != self.case.supervisor_id:
            raise ValidationError(_("Session supervisor must match case supervisor."))

    def save(self, *args, **kwargs):
        # Auto-sync supervisor from case if missing
        if not self.supervisor_id and self.case and self.case.supervisor_id:
            self.supervisor_id = self.case.supervisor_id

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Session {self.id} - {self.case_id}"
