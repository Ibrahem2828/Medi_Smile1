# apps/evaluations/models.py
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Role


# ============================================================
# Enums
# ============================================================

class EvaluationStatus(models.TextChoices):
    CREATED = "created", _("Created")
    UNDER_REVIEW = "under_review", _("Under Review")
    ADJUSTED = "adjusted", _("Adjusted")
    FINALIZED = "finalized", _("Finalized")


class EvaluationTargetType(models.TextChoices):
    CASE = "case", _("Case")
    SESSION = "session", _("Session")
    APPOINTMENT = "appointment", _("Appointment")
    STUDENT = "student", _("Student")
    SUPERVISOR = "supervisor", _("Supervisor")


# ============================================================
# Models
# ============================================================

class Evaluation(models.Model):
    """
    Academic & clinical evaluation.

    Core rules:
    - Evaluator role is stored explicitly (hierarchical evaluation).
    - Target is one of: case / session / appointment / student / supervisor.
    - FINALIZED evaluations are immutable.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    # ============================================================
    # Academic Scope
    # ============================================================

    university = models.ForeignKey(
        "universities.University",
        on_delete=models.PROTECT,
        related_name="evaluations",
        verbose_name=_("University"),
    )

    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="given_evaluations",
        limit_choices_to={
            "role__name__in": [
                Role.PATIENT,
                Role.STUDENT,
                Role.SUPERVISOR,
                Role.UNIVERSITY_ADMIN,
            ]
        },
        verbose_name=_("Evaluator"),
        help_text=_("User who performed the evaluation"),
    )

    evaluator_role = models.CharField(
        max_length=30,
        choices=Role.ROLE_CHOICES,
        verbose_name=_("Evaluator Role"),
        help_text=_("Role snapshot at the time of evaluation"),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_evaluations",
        limit_choices_to={"role__name": Role.STUDENT},
        verbose_name=_("Student"),
        null=True,
        blank=True,
    )

    # ============================================================
    # Evaluation Target
    # ============================================================

    target_type = models.CharField(
        max_length=20,
        choices=EvaluationTargetType.choices,
        verbose_name=_("Evaluation Target Type"),
    )

    target_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("Target ID"),
        help_text=_("UUID of the evaluated target (case/appointment/student/etc.)"),
    )

    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.PROTECT,
        related_name="evaluations",
        null=True,
        blank=True,
        verbose_name=_("Case"),
    )

    session = models.ForeignKey(
        "cases.CaseSession",
        on_delete=models.PROTECT,
        related_name="evaluations",
        null=True,
        blank=True,
        verbose_name=_("Session"),
    )

    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        related_name="evaluations",
        null=True,
        blank=True,
        verbose_name=_("Appointment"),
    )

    # ============================================================
    # Evaluation Content
    # ============================================================

    status = models.CharField(
        max_length=20,
        choices=EvaluationStatus.choices,
        default=EvaluationStatus.CREATED,
        verbose_name=_("Status"),
    )

    score = models.PositiveSmallIntegerField(
        verbose_name=_("Original Score"),
        help_text=_("Score from 0 to 100"),
    )

    final_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Final Score"),
        help_text=_("Final score after adjustments (0-100)"),
    )

    rubric = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Rubric"),
        help_text=_("Flexible evaluation criteria stored as JSON"),
    )

    comment = models.TextField(
        blank=True,
        verbose_name=_("Evaluator Comment"),
    )

    # ============================================================
    # Timestamps
    # ============================================================

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Submitted At"),
    )

    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Finalized At"),
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
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
        db_table = "evaluations"
        verbose_name = _("Evaluation")
        verbose_name_plural = _("Evaluations")
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                check=models.Q(score__gte=0) & models.Q(score__lte=100),
                name="evaluation_score_between_0_and_100",
            ),
            models.CheckConstraint(
                check=models.Q(final_score__isnull=True) | (models.Q(final_score__gte=0) & models.Q(final_score__lte=100)),
                name="evaluation_final_score_between_0_and_100",
            ),
            models.CheckConstraint(
                check=(
                    (
                        models.Q(target_type=EvaluationTargetType.CASE) &
                        models.Q(case__isnull=False) &
                        models.Q(session__isnull=True) &
                        models.Q(appointment__isnull=True)
                    ) |
                    (
                        models.Q(target_type=EvaluationTargetType.SESSION) &
                        models.Q(case__isnull=True) &
                        models.Q(session__isnull=False) &
                        models.Q(appointment__isnull=True)
                    ) |
                    (
                        models.Q(target_type=EvaluationTargetType.APPOINTMENT) &
                        models.Q(case__isnull=True) &
                        models.Q(session__isnull=True) &
                        models.Q(appointment__isnull=False)
                    ) |
                    (
                        models.Q(target_type=EvaluationTargetType.STUDENT) &
                        models.Q(case__isnull=True) &
                        models.Q(session__isnull=True) &
                        models.Q(appointment__isnull=True)
                    ) |
                    (
                        models.Q(target_type=EvaluationTargetType.SUPERVISOR) &
                        models.Q(case__isnull=True) &
                        models.Q(session__isnull=True) &
                        models.Q(appointment__isnull=True)
                    )
                ),
                name="evaluation_target_consistency",
            ),
            models.UniqueConstraint(
                fields=["evaluator", "target_type", "target_id"],
                condition=models.Q(target_id__isnull=False),
                name="unique_evaluation_per_target",
            ),
        ]

    # ============================================================
    # Validation
    # ============================================================

    def clean(self):
        """
        Defensive validation (in addition to DB constraints).
        """

        # Student must be student
        if self.student_id and getattr(getattr(self.student, "role", None), "name", None) != Role.STUDENT:
            raise ValidationError({"student": _("Selected user must be a student.")})

        evaluator_role = getattr(getattr(self.evaluator, "role", None), "name", None)
        if evaluator_role not in {
            Role.PATIENT,
            Role.STUDENT,
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
        }:
            raise ValidationError({"evaluator": _("Evaluator role is not allowed.")})

        if self.student and self.university:
            student_university_id = getattr(getattr(self.student, "studentprofile_profile", None), "university_id", None)
            if student_university_id and student_university_id != self.university_id:
                raise ValidationError(_("Student must belong to the same university as the evaluation."))

        # Target consistency (defensive)
        targets = {
            EvaluationTargetType.CASE: self.case,
            EvaluationTargetType.SESSION: self.session,
            EvaluationTargetType.APPOINTMENT: self.appointment,
            EvaluationTargetType.STUDENT: self.student,
        }

        for t_type, value in targets.items():
            if self.target_type == t_type and value is None:
                raise ValidationError(_("%(type)s evaluation requires its related object.") % {"type": t_type})
            if self.target_type != t_type and value is not None:
                raise ValidationError(
                    _("%(type)s object must be null when target_type != %(type)s.")
                    % {"type": t_type}
                )

        if self.target_type == EvaluationTargetType.CASE and self.case_id and self.target_id and self.target_id != self.case_id:
            raise ValidationError({"target_id": _("Target id must match the case id.")})
        if self.target_type == EvaluationTargetType.SESSION and self.session_id and self.target_id and self.target_id != self.session_id:
            raise ValidationError({"target_id": _("Target id must match the session id.")})
        if self.target_type == EvaluationTargetType.APPOINTMENT and self.appointment_id and self.target_id and self.target_id != self.appointment_id:
            raise ValidationError({"target_id": _("Target id must match the appointment id.")})
        if self.target_type == EvaluationTargetType.STUDENT and self.student_id and self.target_id and self.target_id != self.student_id:
            raise ValidationError({"target_id": _("Target id must match the student id.")})

        if self.target_type == EvaluationTargetType.SUPERVISOR and not self.target_id:
            raise ValidationError({"target_id": _("Supervisor target_id is required.")})

        if not self.target_id:
            raise ValidationError({"target_id": _("Target id is required.")})

    # ============================================================
    # Properties
    # ============================================================

    @property
    def is_locked(self) -> bool:
        """Final evaluations cannot be modified."""
        return self.status == EvaluationStatus.FINALIZED

    def __str__(self):
        return f"Evaluation ({self.get_target_type_display()}) - {self.evaluator}"


class EvaluationAdjustment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="adjustments",
        verbose_name=_("Evaluation"),
    )

    adjusted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evaluation_adjustments",
        verbose_name=_("Adjusted By"),
    )

    adjusted_role = models.CharField(
        max_length=30,
        choices=Role.ROLE_CHOICES,
        verbose_name=_("Adjusted Role"),
    )

    old_score = models.PositiveSmallIntegerField(verbose_name=_("Old Score"))
    new_score = models.PositiveSmallIntegerField(verbose_name=_("New Score"))

    reason = models.TextField(verbose_name=_("Adjustment Reason"))

    adjusted_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Adjusted At"))

    class Meta:
        db_table = "evaluation_adjustments"
        verbose_name = _("Evaluation Adjustment")
        verbose_name_plural = _("Evaluation Adjustments")
        ordering = ["-adjusted_at"]
        indexes = [
            models.Index(fields=["evaluation", "adjusted_at"], name="idx_eval_adj_eval_time"),
            models.Index(fields=["adjusted_by"], name="idx_eval_adj_by"),
        ]

    def __str__(self) -> str:
        return f"Adjustment {self.id} for Evaluation {self.evaluation_id}"
