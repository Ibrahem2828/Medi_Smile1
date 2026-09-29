from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0003_community_approval_log_and_soft_delete"),
    ]

    operations = [
        migrations.AlterField(
            model_name="content",
            name="content_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("image", "Image"),
                    ("case", "Clinical Case"),
                    ("video", "Video"),
                ],
                max_length=20,
                verbose_name="Content Type",
            ),
        ),
        migrations.AddField(
            model_name="content",
            name="image_large",
            field=models.ImageField(blank=True, null=True, upload_to="community/content/large/", verbose_name="Large Image"),
        ),
        migrations.AddField(
            model_name="content",
            name="image_medium",
            field=models.ImageField(blank=True, null=True, upload_to="community/content/medium/", verbose_name="Medium Image"),
        ),
        migrations.AddField(
            model_name="content",
            name="image_thumb",
            field=models.ImageField(blank=True, null=True, upload_to="community/content/thumb/", verbose_name="Thumbnail Image"),
        ),
    ]
