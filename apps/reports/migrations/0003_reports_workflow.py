import json
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def populate_reports(apps, schema_editor):
    Report = apps.get_model("reports", "Report")

    for report in Report.objects.all():
        if not report.author_id:
            report.author_id = report.student_id or report.generated_by_id

        if report.author_id and not report.author_role:
            try:
                report.author_role = report.author.role.name
            except Exception:
                report.author_role = ""

        if not report.target_type or not report.target_id:
            if report.case_id:
                report.target_type = "case"
                report.target_id = report.case_id
            elif report.student_id:
                report.target_type = "student"
                report.target_id = report.student_id
            else:
                report.target_type = "university"
                report.target_id = report.university_id

        if not report.status:
            report.status = "locked"
            report.locked_at = report.generated_at or report.created_at
            report.approved_at = report.reviewed_at or report.generated_at or report.created_at
            if report.supervisor_id and not report.approved_by_id:
                report.approved_by_id = report.supervisor_id

        if report.content:
            try:
                json.loads(report.content)
            except Exception:
                report.content = json.dumps({"text": report.content})

        report.save()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0002_rename_reports_student_report_type_idx_reports_student_359caa_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="author",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="authored_reports",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Author",
                help_text="User who created the report",
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="author_role",
            field=models.CharField(blank=True, max_length=30, verbose_name="Author Role", help_text="Role snapshot at creation time"),
        ),
        migrations.AddField(
            model_name="report",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Approved At"),
        ),
        migrations.AddField(
            model_name="report",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="approved_reports",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Approved By",
                limit_choices_to={"role__name": "supervisor"},
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="locked_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Locked At"),
        ),
        migrations.AddField(
            model_name="report",
            name="rejected_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Rejected At"),
        ),
        migrations.AddField(
            model_name="report",
            name="review_notes",
            field=models.TextField(blank=True, null=True, verbose_name="Review Notes", help_text="Supervisor notes for approval/rejection."),
        ),
        migrations.AddField(
            model_name="report",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("submitted", "Submitted"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("locked", "Locked"),
                ],
                default="draft",
                max_length=20,
                verbose_name="Status",
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="submitted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Submitted At"),
        ),
        migrations.AddField(
            model_name="report",
            name="target_id",
            field=models.UUIDField(blank=True, null=True, verbose_name="Target ID", help_text="Primary target identifier (case/student/course/university).", db_index=True),
        ),
        migrations.AddField(
            model_name="report",
            name="target_type",
            field=models.CharField(
                blank=True,
                null=True,
                choices=[
                    ("case", "Case"),
                    ("student", "Student"),
                    ("course", "Course"),
                    ("university", "University"),
                ],
                max_length=20,
                verbose_name="Target Type",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="student",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="academic_reports",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Student",
                help_text="Student this report belongs to",
                limit_choices_to={"role__name": "student"},
                db_index=True,
            ),
        ),
        migrations.RunPython(populate_reports, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="report",
            name="content",
            field=models.JSONField(blank=True, null=True, verbose_name="Content", help_text="Structured JSON content for the report"),
        ),
        migrations.AlterField(
            model_name="report",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="authored_reports",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Author",
                help_text="User who created the report",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="target_type",
            field=models.CharField(
                choices=[
                    ("case", "Case"),
                    ("student", "Student"),
                    ("course", "Course"),
                    ("university", "University"),
                ],
                max_length=20,
                verbose_name="Target Type",
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="target_id",
            field=models.UUIDField(verbose_name="Target ID", help_text="Primary target identifier (case/student/course/university).", db_index=True),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["target_type", "target_id"], name="reports_target_idx"),
        ),
    ]
