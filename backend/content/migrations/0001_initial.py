# Generated for the initial content-tracker schema.

import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ContentItem",
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
                ("title", models.CharField(max_length=500)),
                (
                    "content_type",
                    models.CharField(
                        choices=[
                            ("video", "Video"),
                            ("tv", "TV"),
                            ("radio", "Radio"),
                            ("podcast", "Podcast"),
                            ("book", "Book"),
                            ("manga", "Manga"),
                            ("article", "Article"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("planned", "Planned"),
                            ("active", "Active"),
                            ("completed", "Completed"),
                            ("dropped", "Dropped"),
                        ],
                        db_index=True,
                        default="planned",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("duration_seconds", models.PositiveIntegerField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="content.contentitem",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "title"],
            },
        ),
        migrations.CreateModel(
            name="ConsumptionHistory",
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
                ("consumed_at", models.DateTimeField()),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                    ),
                ),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "content_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consumption_history",
                        to="content.contentitem",
                    ),
                ),
            ],
            options={
                "ordering": ["-consumed_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ContentLink",
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
                ("url", models.URLField(max_length=2000, unique=True)),
                (
                    "link_type",
                    models.CharField(
                        choices=[("source", "Source"), ("info", "Information")],
                        default="source",
                        max_length=20,
                    ),
                ),
                ("source", models.CharField(blank=True, max_length=100)),
                ("external_id", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "content_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="links",
                        to="content.contentitem",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="contentitem",
            index=models.Index(
                fields=["content_type", "status"],
                name="content_con_content_0d54f9_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="contentlink",
            constraint=models.UniqueConstraint(
                condition=~models.Q(source="") & ~models.Q(external_id=""),
                fields=("source", "external_id"),
                name="unique_source_external_id",
            ),
        ),
    ]
}
