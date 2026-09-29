from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("universities", "0003_course"),
        ("accounts", "0002_alter_patientprofile_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientprofile",
            name="university",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="patients",
                to="universities.university",
                verbose_name="University",
            ),
        ),
    ]
