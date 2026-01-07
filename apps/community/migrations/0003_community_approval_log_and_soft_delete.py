import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def map_content_types(apps, schema_editor):
    Content = apps.get_model("community", "Content")
    Content.objects.filter(content_type="article").update(content_type="text")
    Content.objects.filter(content_type="document").update(content_type="text")
    Content.objects.filter(content_type="link").update(content_type="text")


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0002_remove_contentlike_community_like_content_user_idx_and_more"),
        ("universities", "0003_course"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(map_content_types, migrations.RunPython.noop),
        migrations.AddField(
            model_name="content",
            name="is_deleted",
            field=models.BooleanField(default=False, verbose_name="Deleted"),
        ),
        migrations.AddField(
            model_name="content",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
        ),
        migrations.AddField(
            model_name="content",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deleted_community_content",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Deleted By",
            ),
        ),
        migrations.AddIndex(
            model_name="content",
            index=models.Index(fields=["university", "status"], name="community_university_status_idx"),
        ),
        migrations.CreateModel(
            name="CommunityApprovalLog",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                (
                    "decision",
                    models.CharField(
                        choices=[("approved", "Approved"), ("rejected", "Rejected")],
                        max_length=20,
                        verbose_name="Decision",
                    ),
                ),
                ("reason", models.TextField(blank=True, null=True, verbose_name="Reason")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                (
                    "approving_supervisor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="community_approvals",
                        to=settings.AUTH_USER_MODEL,
                        limit_choices_to={"role__name": "supervisor"},
                        verbose_name="Approving Supervisor",
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="community_posts_approved",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Author",
                    ),
                ),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="approval_logs",
                        to="community.content",
                        verbose_name="Post",
                    ),
                ),
                (
                    "university",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="community_approval_logs",
                        to="universities.university",
                        verbose_name="University",
                    ),
                ),
            ],
            options={
                "verbose_name": "Community Approval Log",
                "verbose_name_plural": "Community Approval Logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="communityapprovallog",
            index=models.Index(fields=["university", "decision"], name="community_approval_decision_idx"),
        ),
        migrations.AddIndex(
            model_name="communityapprovallog",
            index=models.Index(fields=["post", "created_at"], name="community_approval_post_created_idx"),
        ),
    ]
