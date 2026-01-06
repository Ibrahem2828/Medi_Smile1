from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("universities", "0003_course"),
        ("accounts", "0003_patientprofile_university"),
        ("cases", "0003_case_ai_metadata_case_is_ai_critical"),
    ]

    operations = [
        migrations.AlterField(
            model_name="case",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "New (Initial Diagnosis)"),
                    ("pending_assignment", "Pending Assignment"),
                    ("accepted", "Accepted by Supervisor"),
                    ("rejected", "Rejected by Supervisor"),
                    ("needs_assignment_approval", "Needs Assignment Approval"),
                    ("assigned", "Assigned to Student"),
                    ("in_progress", "In Progress"),
                    ("completed", "Completed"),
                    ("closed", "Closed (Finalized)"),
                ],
                default="new",
                max_length=30,
                verbose_name="Status",
            ),
        ),
        migrations.CreateModel(
            name="AIAnalysisSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("case_id_external", models.CharField(blank=True, max_length=255, null=True)),
                ("request_id", models.CharField(blank=True, max_length=255, null=True)),
                ("session_summary", models.JSONField(blank=True, null=True)),
                ("ui_hints", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_sessions", to="accounts.user")),
                ("university", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_sessions", to="universities.university")),
            ],
            options={
                "db_table": "ai_analysis_sessions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AIProposedCase",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("proposal_id", models.CharField(max_length=255)),
                ("tooth_id", models.IntegerField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pending_patient", "Pending Patient Decision"), ("rejected_by_patient", "Rejected by Patient"), ("approved_by_patient", "Approved by Patient"), ("rejected_by_supervisor", "Rejected by Supervisor"), ("approved_by_supervisor", "Approved by Supervisor"), ("converted", "Converted to Case")], default="pending_patient", max_length=50)),
                ("fusion_decision", models.JSONField(blank=True, null=True)),
                ("medical_report", models.JSONField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("raw_proposal", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("converted_case", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_proposals", to="cases.case")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="proposals", to="cases.aianalysissession")),
            ],
            options={
                "db_table": "ai_proposed_cases",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="aiproposedcase",
            index=models.Index(fields=["status"], name="idx_ai_proposal_status"),
        ),
        migrations.AddIndex(
            model_name="aiproposedcase",
            index=models.Index(fields=["proposal_id"], name="idx_ai_proposal_pid"),
        ),
    ]
