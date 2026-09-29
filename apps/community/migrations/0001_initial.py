import uuid
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("universities", "0003_course"),
    ]

    operations = [
        migrations.CreateModel(
            name="Content",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("title", models.CharField(max_length=200, verbose_name="Title")),
                ("description", models.TextField(verbose_name="Description")),
                (
                    "content_type",
                    models.CharField(
                        choices=[
                            ("article", "Article"),
                            ("video", "Video"),
                            ("document", "Document"),
                            ("image", "Image"),
                            ("link", "External Link"),
                        ],
                        max_length=20,
                        verbose_name="Content Type",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("medical", "Medical"),
                            ("educational", "Educational"),
                            ("research", "Research"),
                            ("news", "News"),
                            ("general", "General"),
                        ],
                        max_length=20,
                        verbose_name="Category",
                    ),
                ),
                ("file", models.FileField(blank=True, null=True, upload_to="community/content/", verbose_name="Attached File")),
                ("url", models.URLField(blank=True, null=True, verbose_name="External URL")),
                ("tags", models.CharField(blank=True, max_length=500, null=True, verbose_name="Tags (comma separated)")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending Approval"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Approval Status",
                    ),
                ),
                ("approved_at", models.DateTimeField(blank=True, null=True, verbose_name="Approved At")),
                ("rejection_reason", models.TextField(blank=True, null=True, verbose_name="Rejection Reason")),
                ("is_public", models.BooleanField(default=True, help_text="If false, visible only inside university.", verbose_name="Publicly Visible")),
                ("is_featured", models.BooleanField(default=False, verbose_name="Featured Content")),
                ("view_count", models.PositiveIntegerField(default=0, verbose_name="View Count")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={"role__name__in": ["supervisor", "university_admin", "tech_support"]},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approved_content",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Approved / Rejected By",
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="community_content",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Author",
                    ),
                ),
                (
                    "university",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="community_content",
                        to="universities.university",
                        verbose_name="University",
                    ),
                ),
            ],
            options={
                "db_table": "community_content",
                "ordering": ["-created_at"],
                "verbose_name": "Community Content",
                "verbose_name_plural": "Community Content",
            },
        ),
        migrations.CreateModel(
            name="ContentComment",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("text", models.TextField(verbose_name="Comment")),
                ("is_approved", models.BooleanField(default=True, help_text="Future moderation support.", verbose_name="Approved")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                (
                    "content",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="community.content",
                        verbose_name="Content",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_comments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "db_table": "community_content_comments",
                "ordering": ["created_at"],
                "verbose_name": "Content Comment",
                "verbose_name_plural": "Content Comments",
            },
        ),
        migrations.CreateModel(
            name="ContentLike",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "content",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="likes",
                        to="community.content",
                        verbose_name="Content",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_likes",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "db_table": "community_content_likes",
                "verbose_name": "Content Like",
                "verbose_name_plural": "Content Likes",
            },
        ),
        migrations.AddConstraint(
            model_name="contentlike",
            constraint=models.UniqueConstraint(fields=("content", "user"), name="unique_like_per_user_per_content"),
        ),
        migrations.AddIndex(
            model_name="content",
            index=models.Index(fields=["status"], name="community_content_status_idx"),
        ),
        migrations.AddIndex(
            model_name="content",
            index=models.Index(fields=["author"], name="community_content_author_idx"),
        ),
        migrations.AddIndex(
            model_name="content",
            index=models.Index(fields=["university"], name="community_content_university_idx"),
        ),
        migrations.AddIndex(
            model_name="contentlike",
            index=models.Index(fields=["content", "user"], name="community_like_content_user_idx"),
        ),
    ]
