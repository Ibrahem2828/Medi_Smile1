import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("universities", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Report",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "report_type",
                    models.CharField(
                        choices=[
                            ("clinical_case", "Clinical Case Report"),
                            ("session_report", "Session Report"),
                            ("academic", "Academic Performance"),
                            ("evaluation", "Evaluation Summary"),
                            ("summary", "Period Summary"),
                            ("media_report", "Media (Before/After)"),
                            ("supervisor_review", "Supervisor Review"),
                            ("administrative", "Administrative Oversight"),
                            ("other", "Other"),
                        ],
                        db_index=True,
                        max_length=50,
                        verbose_name="Report Type",
                    ),
                ),
                ("case_id", models.UUIDField(blank=True, db_index=True, null=True, verbose_name="Case ID")),
                ("session_id", models.UUIDField(blank=True, db_index=True, null=True, verbose_name="Session ID")),
                (
                    "title",
                    models.CharField(
                        blank=True,
                        help_text="Optional descriptive title for the report",
                        max_length=200,
                        null=True,
                        verbose_name="Title",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional notes or explanation for this report",
                        null=True,
                        verbose_name="Description",
                    ),
                ),
                (
                    "content",
                    models.TextField(
                        blank=True,
                        help_text="Rich text / markdown content for the report",
                        null=True,
                        verbose_name="Content",
                    ),
                ),
                (
                    "file_url",
                    models.TextField(
                        blank=True,
                        help_text="Absolute or relative path to the generated report file (optional for media/content-based reports)",
                        null=True,
                        verbose_name="File URL",
                    ),
                ),
                (
                    "attachments",
                    models.JSONField(
                        blank=True,
                        help_text="List of attachments with types (before/during/after/file).",
                        null=True,
                        verbose_name="Attachments",
                    ),
                ),
                (
                    "snapshot_data",
                    models.JSONField(
                        blank=True,
                        help_text="Optional frozen snapshot of aggregated data (for statistics/progress).",
                        null=True,
                        verbose_name="Snapshot Data",
                    ),
                ),
                (
                    "score",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        help_text="Optional numeric score (0-100).",
                        null=True,
                        verbose_name="Score",
                    ),
                ),
                (
                    "feedback",
                    models.TextField(
                        blank=True,
                        help_text="Supervisor feedback for the report.",
                        null=True,
                        verbose_name="Feedback / Review",
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="Reviewed At")),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Soft visibility flag (reports are never deleted)",
                        verbose_name="Is Active",
                    ),
                ),
                ("generated_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Generated At")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
                (
                    "generated_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who generated this report",
                        limit_choices_to={
                            "role__name__in": ["supervisor", "university_admin", "tech_support"]
                        },
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="generated_reports",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Generated By",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        help_text="Student this report belongs to",
                        limit_choices_to={"role__name": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="academic_reports",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Student",
                    ),
                ),
                (
                    "supervisor",
                    models.ForeignKey(
                        blank=True,
                        help_text="Supervisor linked to this report or reviewer",
                        limit_choices_to={"role__name": "supervisor"},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_reports",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Supervisor",
                    ),
                ),
                (
                    "university",
                    models.ForeignKey(
                        help_text="University that owns this report",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports",
                        to="universities.university",
                        verbose_name="University",
                    ),
                ),
            ],
            options={
                "verbose_name": "Report",
                "verbose_name_plural": "Reports",
                "db_table": "reports",
                "ordering": ["-generated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["student", "report_type"], name="reports_student_report_type_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["university", "report_type"], name="reports_university_report_type_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["generated_at"], name="reports_generated_at_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["case_id"], name="reports_case_id_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["session_id"], name="reports_session_id_idx"),
        ),
    ]
