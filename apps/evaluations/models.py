import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class EvaluationStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    FINAL = "final", _("Final")


class EvaluationTargetType(models.TextChoices):
    CASE = "case", _("Case")
    SESSION = "session", _("Session")
    APPOINTMENT = "appointment", _("Appointment")


class Evaluation(models.Model):
    """
    Academic & clinical evaluation model.
    Core evaluator: Supervisor
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    # =========================
    # Academic Scope
    # =========================
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
        limit_choices_to={"role__in": ["supervisor", "university_admin"]},
        verbose_name=_("Evaluator"),
        help_text=_("Supervisor or university admin who performed the evaluation"),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_evaluations",
        limit_choices_to={"role": "student"},
        verbose_name=_("Student"),
    )

    # =========================
    # Evaluation Target
    # =========================
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

    # =========================
    # Evaluation Content
    # =========================
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

    # =========================
    # Timestamps
    # =========================
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

    # =========================
    # Meta
    # =========================
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
        ]

    # =========================
    # Business Logic
    # =========================
    def clean(self):
        """
        Ensure target_type matches exactly one related object.
        """
        targets = {
            EvaluationTargetType.CASE: self.case,
            EvaluationTargetType.SESSION: self.session,
            EvaluationTargetType.APPOINTMENT: self.appointment,
        }

        for t_type, value in targets.items():
            if self.target_type == t_type and value is None:
                raise ValueError(f"{t_type} evaluation requires its related object.")
            if self.target_type != t_type and value is not None:
                raise ValueError(f"{t_type} object must be null when target_type != {t_type}.")

    @property
    def is_locked(self) -> bool:
        """Final evaluations cannot be modified."""
        return self.status == EvaluationStatus.FINAL

    def __str__(self):
        return f"Evaluation ({self.get_target_type_display()}) - {self.student}"
