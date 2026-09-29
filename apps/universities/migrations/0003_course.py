from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("universities", "0002_alter_academicprogram_unique_together_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("code", models.CharField(max_length=50)),
                ("description", models.TextField(blank=True, null=True)),
                ("credits", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "academic_year",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="courses",
                        to="universities.academicyear",
                        verbose_name="Academic Year",
                    ),
                ),
                (
                    "faculty",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="courses",
                        to="universities.faculty",
                        verbose_name="Faculty",
                    ),
                ),
                (
                    "program",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="courses",
                        to="universities.academicprogram",
                        verbose_name="Academic Program",
                    ),
                ),
                (
                    "students",
                    models.ManyToManyField(
                        blank=True,
                        limit_choices_to={"role__name": "student"},
                        related_name="enrolled_courses",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Students",
                    ),
                ),
                (
                    "supervisor",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={"role__name": "supervisor"},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="supervised_courses",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Supervisor",
                    ),
                ),
                (
                    "university",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="courses",
                        to="universities.university",
                        verbose_name="University",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course",
                "verbose_name_plural": "Courses",
                "db_table": "courses",
                "ordering": ["name"],
            },
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(
                fields=["university", "is_active"], name="idx_course_univ_active"
            ),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(fields=["code"], name="idx_course_code"),
        ),
        migrations.AddConstraint(
            model_name="course",
            constraint=models.UniqueConstraint(
                fields=("university", "code"), name="uq_course_university_code"
            ),
        ),
    ]
