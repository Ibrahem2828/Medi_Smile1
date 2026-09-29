# Generated manually to support course-based threads and flexible participants.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("universities", "0003_course"),
        ("messaging", "0002_rename_messaging_message_room_idx_messaging_m_room_id_1cc8af_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="thread_type",
            field=models.CharField(choices=[("case", "Case"), ("course", "Course")], default="case", max_length=20, verbose_name="Thread Type"),
        ),
        migrations.AddField(
            model_name="room",
            name="course",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="chat_rooms", to="universities.course", verbose_name="Course"),
        ),
        migrations.AddField(
            model_name="room",
            name="participant_supervisor",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="supervisor_chat_rooms", to=settings.AUTH_USER_MODEL, verbose_name="Supervisor"),
        ),
        migrations.AlterField(
            model_name="room",
            name="case",
            field=models.OneToOneField(blank=True, help_text="Each case has exactly one messaging room", null=True, on_delete=django.db.models.deletion.CASCADE, related_name="chat_room", to="cases.case", verbose_name="Case"),
        ),
        migrations.AlterField(
            model_name="room",
            name="participant_patient",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="patient_chat_rooms", to=settings.AUTH_USER_MODEL, verbose_name="Patient"),
        ),
        migrations.AlterField(
            model_name="room",
            name="participant_student",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="student_chat_rooms", to=settings.AUTH_USER_MODEL, verbose_name="Student"),
        ),
        migrations.AddIndex(
            model_name="room",
            index=models.Index(fields=["course"], name="messaging_r_course_id_idx"),
        ),
        migrations.AddIndex(
            model_name="room",
            index=models.Index(fields=["participant_supervisor"], name="messaging_r_partici_sup_idx"),
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.CheckConstraint(check=~models.Q(participant_supervisor=models.F("participant_student")), name="room_supervisor_student_must_be_different"),
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.UniqueConstraint(fields=("course", "participant_student", "participant_supervisor", "thread_type"), name="room_unique_course_thread"),
        ),
    ]
