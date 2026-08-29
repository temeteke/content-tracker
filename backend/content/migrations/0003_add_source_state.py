from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0002_use_url_as_link_identity"),
    ]

    operations = [
        migrations.CreateModel(
            name="SourceState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("source_key", models.CharField(max_length=128, unique=True)),
                ("sync_state", models.JSONField(blank=True, default=dict)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["source_key"],
            },
        ),
    ]
