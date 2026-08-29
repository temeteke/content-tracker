import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ContentType(models.TextChoices):
    VIDEO = "video", "Video"
    TV = "tv", "TV"
    RADIO = "radio", "Radio"
    PODCAST = "podcast", "Podcast"
    BOOK = "book", "Book"
    MANGA = "manga", "Manga"
    ARTICLE = "article", "Article"
    OTHER = "other", "Other"


class ConsumptionStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    DROPPED = "dropped", "Dropped"


class ContentItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.OTHER,
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    status = models.CharField(
        max_length=20,
        choices=ConsumptionStatus.choices,
        default=ConsumptionStatus.PLANNED,
        db_index=True,
    )
    description = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "title"]
        indexes = [
            models.Index(
                fields=["content_type", "status"],
                name="content_type_status_idx",
            )
        ]

    def __str__(self) -> str:
        return self.title


class LinkType(models.TextChoices):
    SOURCE = "source", "Source"
    INFO = "info", "Information"


class ContentLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="links",
    )
    url = models.URLField(max_length=2000, unique=True)
    link_type = models.CharField(
        max_length=20,
        choices=LinkType.choices,
        default=LinkType.SOURCE,
    )
    source = models.CharField(max_length=100, null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="unique_source_external_id",
            )
        ]

    def __str__(self) -> str:
        return self.url


class ConsumptionHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="consumption_history",
    )
    consumed_at = models.DateTimeField()
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-consumed_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.content_item}: {self.consumed_at.isoformat()}"
