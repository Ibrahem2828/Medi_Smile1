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
    """

    # --------------------------------------------------------
    # Status & Priority
    # --------------------------------------------------------
    class Status(models.TextChoices):
        NEW = "new", _("New (Initial Diagnosis)")
        ACCEPTED = "accepted", _("Accepted by Supervisor")
        REJECTED = "rejected", _("Rejected by Supervisor")
        NEEDS_ASSIGNMENT_APPROVAL = "needs_assignment_approval", _("Needs Assignment Approval")
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
        Status.ACCEPTED,
        Status.NEEDS_ASSIGNMENT_APPROVAL,
        Status.ASSIGNED,
        Status.IN_PROGRESS,
    }

    ALLOWED_TRANSITIONS = {
        Status.NEW: {Status.ACCEPTED, Status.REJECTED},
        Status.ACCEPTED: {Status.NEEDS_ASSIGNMENT_APPROVAL, Status.REJECTED},
        Status.NEEDS_ASSIGNMENT_APPROVAL: {Status.ACCEPTED, Status.ASSIGNED},
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

    # AI metadata (critical AI-created cases)
    is_ai_critical = models.BooleanField(
        default=False,
        verbose_name=_("AI Critical Case"),
        help_text=_("Set when created from AI with high severity/urgency."),
    )
    ai_metadata = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("AI Metadata"),
        help_text=_("Raw AI payload (severity/diagnosis/confidence)."),
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

        # AI critical cases must carry AI metadata
        if self.is_ai_critical and not self.ai_metadata:
            raise ValidationError(_("AI critical cases must include AI metadata."))

        # Role validation (FK-based)
        if self.patient and getattr(self.patient.role, "name", None) != Role.PATIENT:
            raise ValidationError(_("Assigned patient must have role 'patient'."))

        if self.student and getattr(self.student.role, "name", None) != Role.STUDENT:
            raise ValidationError(_("Assigned student must have role 'student'."))

        if self.supervisor and getattr(self.supervisor.role, "name", None) != Role.SUPERVISOR:
            raise ValidationError(_("Assigned supervisor must have role 'supervisor'."))

        # If case is public / pending assignment, university must be set
        if self.is_public or self.status in {self.Status.ACCEPTED, self.Status.NEEDS_ASSIGNMENT_APPROVAL}:
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
        if not self._state.adding:
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

    # Track the student who requested assignment for quick access on the Case
    def apply_to_case(self):
        """
        Helper to set case state when request created.
        """
        if self.case.status == Case.Status.ACCEPTED:
            self.case.status = Case.Status.NEEDS_ASSIGNMENT_APPROVAL
            self.case.is_public = False
            self.case.save(update_fields=["status", "is_public", "updated_at"])

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

        # University scoping: only students from the same university can see/request
        student_university_id = getattr(getattr(self.student, "studentprofile_profile", None), "university_id", None)
        if student_university_id and self.case.university_id and student_university_id != self.case.university_id:
            raise ValidationError(_("You are not eligible to request this case (different university)."))
        if self.case.university_id and not student_university_id:
            raise ValidationError(_("Student must be linked to a university to request this case."))

        # Allowed states for requesting assignment (only enforce for pending/new requests)
        if self._state.adding or self.status == CaseAssignmentRequest.Status.PENDING:
            if self.case.status not in {Case.Status.ACCEPTED, Case.Status.NEEDS_ASSIGNMENT_APPROVAL}:
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


# ============================================================
# AI Analysis Session / Proposed Cases (pre-patient approval)
# ============================================================


class AIAnalysisSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ai_sessions",
    )
    university = models.ForeignKey(
        University,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_sessions",
    )
    case_id_external = models.CharField(max_length=255, blank=True, null=True)
    request_id = models.CharField(max_length=255, blank=True, null=True)
    session_summary = models.JSONField(blank=True, null=True)
    ui_hints = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_analysis_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"AI Session {self.id}"


class AIProposedCase(models.Model):
    class Status(models.TextChoices):
        PENDING_PATIENT = "pending_patient", _("Pending Patient Decision")
        REJECTED_BY_PATIENT = "rejected_by_patient", _("Rejected by Patient")
        APPROVED_BY_PATIENT = "approved_by_patient", _("Approved by Patient")
        REJECTED_BY_SUPERVISOR = "rejected_by_supervisor", _("Rejected by Supervisor")
        APPROVED_BY_SUPERVISOR = "approved_by_supervisor", _("Approved by Supervisor")
        CONVERTED = "converted", _("Converted to Case")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        AIAnalysisSession,
        on_delete=models.CASCADE,
        related_name="proposals",
    )
    proposal_id = models.CharField(max_length=255)
    tooth_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.PENDING_PATIENT,
    )
    fusion_decision = models.JSONField(blank=True, null=True)
    medical_report = models.JSONField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    raw_proposal = models.JSONField(blank=True, null=True)
    converted_case = models.ForeignKey(
        Case,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_proposals",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_proposed_cases"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status"], name="idx_ai_proposal_status"),
            models.Index(fields=["proposal_id"], name="idx_ai_proposal_pid"),
        ]

    def __str__(self):
        return f"Proposal {self.proposal_id}"
