# apps/evaluations/models.py
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import Role


# ============================================================
# Enums
# ============================================================

class EvaluationStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    FINAL = "final", _("Final")


class EvaluationTargetType(models.TextChoices):
    CASE = "case", _("Case")
    SESSION = "session", _("Session")
    APPOINTMENT = "appointment", _("Appointment")


# ============================================================
# Model
# ============================================================

class Evaluation(models.Model):
    """
    Academic & clinical evaluation.

    Core rules:
    - Evaluator: Supervisor or University Admin
    - Student: must belong to same university
    - Exactly ONE target (case OR session OR appointment)
    - FINAL evaluations are immutable
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
                Role.SUPERVISOR,
                Role.UNIVERSITY_ADMIN,
            ]
        },
        verbose_name=_("Evaluator"),
        help_text=_("Supervisor or university admin who performed the evaluation"),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_evaluations",
        limit_choices_to={"role__name": Role.STUDENT},
        verbose_name=_("Student"),
    )

    # ============================================================
    # Evaluation Target
    # ============================================================

    target_type = models.CharField(
        max_length=20,
        choices=EvaluationTargetType.choices,
        verbose_name=_("Evaluation Target Type"),
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
        default=EvaluationStatus.DRAFT,
        verbose_name=_("Status"),
    )

    score = models.PositiveSmallIntegerField(
        verbose_name=_("Score"),
        help_text=_("Score from 0 to 100"),
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
            # Score range safety
            models.CheckConstraint(
                check=models.Q(score__gte=0) & models.Q(score__lte=100),
                name="evaluation_score_between_0_and_100",
            ),

            # Exactly one target must be set
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
                    )
                ),
                name="evaluation_exactly_one_target",
            ),

            # Prevent duplicate evaluations by same evaluator on same target
            models.UniqueConstraint(
                fields=["evaluator", "student", "case"],
                condition=models.Q(case__isnull=False),
                name="unique_case_evaluation_per_evaluator",
            ),
            models.UniqueConstraint(
                fields=["evaluator", "student", "session"],
                condition=models.Q(session__isnull=False),
                name="unique_session_evaluation_per_evaluator",
            ),
            models.UniqueConstraint(
                fields=["evaluator", "student", "appointment"],
                condition=models.Q(appointment__isnull=False),
                name="unique_appointment_evaluation_per_evaluator",
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
        if getattr(getattr(self.student, "role", None), "name", None) != Role.STUDENT:
            raise ValidationError({"student": _("Selected user must be a student.")})

        # Evaluator role check (allow patient feedback)
        if getattr(getattr(self.evaluator, "role", None), "name", None) not in {
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
            Role.PATIENT,
        }:
            raise ValidationError({"evaluator": _("Evaluator must be supervisor, university admin, or patient.")})

        # University consistency
        if self.student and self.university and getattr(self.student, "university_id", None) != self.university_id:
            raise ValidationError(_("Student must belong to the same university as the evaluation."))

        # Target consistency (defensive – DB already enforces)
        targets = {
            EvaluationTargetType.CASE: self.case,
            EvaluationTargetType.SESSION: self.session,
            EvaluationTargetType.APPOINTMENT: self.appointment,
        }

        for t_type, value in targets.items():
            if self.target_type == t_type and value is None:
                raise ValidationError(_("%(type)s evaluation requires its related object.") % {"type": t_type})
            if self.target_type != t_type and value is not None:
                raise ValidationError(
                    _("%(type)s object must be null when target_type != %(type)s.")
                    % {"type": t_type}
                )

    # ============================================================
    # Properties
    # ============================================================

    @property
    def is_locked(self) -> bool:
        """Final evaluations cannot be modified."""
        return self.status == EvaluationStatus.FINAL

    def __str__(self):
        return f"Evaluation ({self.get_target_type_display()}) - {self.student}"
