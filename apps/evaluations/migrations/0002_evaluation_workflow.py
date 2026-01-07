import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_evaluations(apps, schema_editor):
    Evaluation = apps.get_model("evaluations", "Evaluation")
    User = apps.get_model("accounts", "User")
    Role = apps.get_model("accounts", "Role")

    role_map = {role.id: role.name for role in Role.objects.all()}
    user_role_map = {
        user.id: role_map.get(user.role_id, "")
        for user in User.objects.all().only("id", "role_id")
    }

    for evaluation in Evaluation.objects.all().iterator():
        evaluation.evaluator_role = evaluation.evaluator_role or user_role_map.get(evaluation.evaluator_id, "")

        if evaluation.final_score is None:
            evaluation.final_score = evaluation.score

        if not evaluation.target_id:
            if evaluation.target_type == "case" and evaluation.case_id:
                evaluation.target_id = evaluation.case_id
            elif evaluation.target_type == "session" and evaluation.session_id:
                evaluation.target_id = evaluation.session_id
            elif evaluation.target_type == "appointment" and evaluation.appointment_id:
                evaluation.target_id = evaluation.appointment_id
            elif evaluation.target_type == "student" and evaluation.student_id:
                evaluation.target_id = evaluation.student_id

        if evaluation.status == "draft":
            evaluation.status = "created"
        elif evaluation.status == "submitted":
            evaluation.status = "under_review"
        elif evaluation.status == "final":
            evaluation.status = "finalized"

        evaluation.save(update_fields=["evaluator_role", "final_score", "target_id", "status"])


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="evaluation",
            name="evaluator_role",
            field=models.CharField(
                choices=[
                    ("patient", "Patient"),
                    ("student", "Student"),
                    ("supervisor", "Supervisor"),
                    ("university_admin", "University Admin"),
                    ("tech_support", "Tech Support"),
                ],
                default="supervisor",
                max_length=30,
                verbose_name="Evaluator Role",
                help_text="Role snapshot at the time of evaluation",
            ),
        ),
        migrations.AddField(
            model_name="evaluation",
            name="final_score",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Final Score", help_text="Final score after adjustments (0-100)"),
        ),
        migrations.AddField(
            model_name="evaluation",
            name="target_id",
            field=models.UUIDField(blank=True, null=True, verbose_name="Target ID", help_text="UUID of the evaluated target (case/appointment/student/etc.)"),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="evaluator",
            field=models.ForeignKey(
                help_text="User who performed the evaluation",
                limit_choices_to={"role__name__in": ["patient", "student", "supervisor", "university_admin"]},
                on_delete=django.db.models.deletion.PROTECT,
                related_name="given_evaluations",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Evaluator",
            ),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="student",
            field=models.ForeignKey(
                blank=True,
                null=True,
                limit_choices_to={"role__name": "student"},
                on_delete=django.db.models.deletion.PROTECT,
                related_name="received_evaluations",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Student",
            ),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="status",
            field=models.CharField(
                choices=[
                    ("created", "Created"),
                    ("under_review", "Under Review"),
                    ("adjusted", "Adjusted"),
                    ("finalized", "Finalized"),
                ],
                default="created",
                max_length=20,
                verbose_name="Status",
            ),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="target_type",
            field=models.CharField(
                choices=[
                    ("case", "Case"),
                    ("session", "Session"),
                    ("appointment", "Appointment"),
                    ("student", "Student"),
                    ("supervisor", "Supervisor"),
                ],
                max_length=20,
                verbose_name="Evaluation Target Type",
            ),
        ),
        migrations.RunPython(migrate_evaluations, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="evaluation",
            name="evaluation_exactly_one_target",
        ),
        migrations.RemoveConstraint(
            model_name="evaluation",
            name="unique_case_evaluation_per_evaluator",
        ),
        migrations.RemoveConstraint(
            model_name="evaluation",
            name="unique_session_evaluation_per_evaluator",
        ),
        migrations.RemoveConstraint(
            model_name="evaluation",
            name="unique_appointment_evaluation_per_evaluator",
        ),
        migrations.AddConstraint(
            model_name="evaluation",
            constraint=models.CheckConstraint(
                check=(
                    (models.Q(target_type="case") & models.Q(case__isnull=False) & models.Q(session__isnull=True) & models.Q(appointment__isnull=True))
                    | (models.Q(target_type="session") & models.Q(case__isnull=True) & models.Q(session__isnull=False) & models.Q(appointment__isnull=True))
                    | (models.Q(target_type="appointment") & models.Q(case__isnull=True) & models.Q(session__isnull=True) & models.Q(appointment__isnull=False))
                    | (models.Q(target_type="student") & models.Q(case__isnull=True) & models.Q(session__isnull=True) & models.Q(appointment__isnull=True))
                    | (models.Q(target_type="supervisor") & models.Q(case__isnull=True) & models.Q(session__isnull=True) & models.Q(appointment__isnull=True))
                ),
                name="evaluation_target_consistency",
            ),
        ),
        migrations.AddConstraint(
            model_name="evaluation",
            constraint=models.UniqueConstraint(
                fields=("evaluator", "target_type", "target_id"),
                condition=models.Q(target_id__isnull=False),
                name="unique_evaluation_per_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="evaluation",
            constraint=models.CheckConstraint(
                check=models.Q(final_score__isnull=True) | (models.Q(final_score__gte=0) & models.Q(final_score__lte=100)),
                name="evaluation_final_score_between_0_and_100",
            ),
        ),
        migrations.CreateModel(
            name="EvaluationAdjustment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("adjusted_role", models.CharField(choices=[("patient", "Patient"), ("student", "Student"), ("supervisor", "Supervisor"), ("university_admin", "University Admin"), ("tech_support", "Tech Support")], max_length=30, verbose_name="Adjusted Role")),
                ("old_score", models.PositiveSmallIntegerField(verbose_name="Old Score")),
                ("new_score", models.PositiveSmallIntegerField(verbose_name="New Score")),
                ("reason", models.TextField(verbose_name="Adjustment Reason")),
                ("adjusted_at", models.DateTimeField(auto_now_add=True, verbose_name="Adjusted At")),
                ("adjusted_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="evaluation_adjustments", to=settings.AUTH_USER_MODEL, verbose_name="Adjusted By")),
                ("evaluation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="adjustments", to="evaluations.evaluation", verbose_name="Evaluation")),
            ],
            options={
                "verbose_name": "Evaluation Adjustment",
                "verbose_name_plural": "Evaluation Adjustments",
                "db_table": "evaluation_adjustments",
                "ordering": ["-adjusted_at"],
            },
        ),
        migrations.AddIndex(
            model_name="evaluationadjustment",
            index=models.Index(fields=["evaluation", "adjusted_at"], name="idx_eval_adj_eval_time"),
        ),
        migrations.AddIndex(
            model_name="evaluationadjustment",
            index=models.Index(fields=["adjusted_by"], name="idx_eval_adj_by"),
        ),
    ]
