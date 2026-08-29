from collections.abc import Iterable
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction

from .adapters.base import ContentCandidate
from .models import ContentItem, ContentLink, ContentType, LinkType

validate_http_url = URLValidator(schemes=["http", "https"])


def _is_ancestor(ancestor: ContentItem, item: ContentItem) -> bool:
    current = item.parent
    while current is not None:
        if current.id == ancestor.id:
            return True
        current = current.parent
    return False


def validate_parent_assignment(item: ContentItem, parent: ContentItem | None) -> None:
    if parent is None:
        return
    if parent.id == item.id or _is_ancestor(item, parent):
        raise ValueError("parent assignment would create a hierarchy cycle")


@transaction.atomic
def merge_content_items(*, target_id: UUID, source_id: UUID) -> ContentItem:
    if target_id == source_id:
        raise ValueError("target and source must be different")

    target = ContentItem.objects.select_for_update().get(id=target_id)
    source = ContentItem.objects.select_for_update().get(id=source_id)

    if _is_ancestor(target, source) or _is_ancestor(source, target):
        raise ValueError("items in the same hierarchy branch cannot be merged")

    ContentItem.objects.filter(parent=source).update(parent=target)
    ContentLink.objects.filter(content_item=source).update(content_item=target)
    source.consumption_history.update(content_item=target)

    merged_metadata = dict(source.metadata)
    merged_metadata.update(target.metadata)
    if merged_metadata != target.metadata:
        target.metadata = merged_metadata
        target.save(update_fields=["metadata", "updated_at"])

    source.delete()
    return target


@transaction.atomic
def import_candidates(candidates: Iterable[ContentCandidate]) -> tuple[int, int]:
    created = 0
    updated = 0

    for candidate in candidates:
        title = candidate.title.strip()
        if not title:
            raise ValueError("candidate title must not be empty")
        if candidate.content_type not in ContentType.values:
            raise ValueError(f"unsupported content type: {candidate.content_type}")

        url = candidate.url.strip()
        try:
            validate_http_url(url)
        except ValidationError as exc:
            raise ValueError("candidate url must be a valid HTTP(S) URL") from exc

        link = ContentLink.objects.select_related("content_item").filter(url=url).first()

        if link is None:
            item = ContentItem.objects.create(
                title=title,
                content_type=candidate.content_type,
                published_at=candidate.published_at,
                duration_seconds=candidate.duration_seconds,
                metadata=candidate.metadata,
            )
            ContentLink.objects.create(
                content_item=item,
                url=url,
                link_type=LinkType.SOURCE,
                metadata=candidate.metadata,
            )
            created += 1
            continue

        item = link.content_item
        item.title = title
        item.content_type = candidate.content_type
        item.published_at = candidate.published_at
        item.duration_seconds = candidate.duration_seconds
        item.metadata = {**item.metadata, **candidate.metadata}
        item.save(
            update_fields=[
                "title",
                "content_type",
                "published_at",
                "duration_seconds",
                "metadata",
                "updated_at",
            ]
        )
        link.metadata = {**link.metadata, **candidate.metadata}
        link.save(update_fields=["metadata"])
        updated += 1

    return created, updated
