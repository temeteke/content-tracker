from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="contentlink",
            name="unique_source_external_id",
        ),
        migrations.RemoveField(
            model_name="contentlink",
            name="external_id",
        ),
        migrations.RemoveField(
            model_name="contentlink",
            name="source",
        ),
    ]
