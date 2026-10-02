# Generated manually to make safe AI outcome states explicit.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0003_ai_image_upload"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aidiagnosis",
            name="confidence_level",
            field=models.CharField(
                choices=[("unknown", "Unknown"), ("low", "Low"), ("medium", "Medium"), ("high", "High")],
                default="medium", max_length=20, verbose_name="Confidence Level",
            ),
        ),
        migrations.AlterField(
            model_name="aidiagnosis",
            name="severity_level",
            field=models.CharField(
                choices=[("unknown", "Unknown"), ("low", "Low"), ("moderate", "Moderate"), ("high", "High")],
                default="moderate", max_length=20, verbose_name="Severity Level",
            ),
        ),
        migrations.AlterField(
            model_name="aidiagnosis",
            name="urgency_level",
            field=models.CharField(
                choices=[("unknown", "Unknown"), ("non_urgent", "Non Urgent"), ("urgent", "Urgent")],
                default="non_urgent", max_length=20, verbose_name="Urgency Level",
            ),
        ),
        migrations.AlterField(
            model_name="aidiagnosis",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"), ("completed", "Completed"),
                    ("partial", "Partial Evidence"),
                    ("insufficient_evidence", "Insufficient Evidence"),
                    ("failed", "Failed"), ("reviewed", "Reviewed by Supervisor"),
                ],
                default="pending", max_length=30, verbose_name="Status",
            ),
        ),
    ]
