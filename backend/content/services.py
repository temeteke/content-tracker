from collections.abc import Iterable
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .adapters.base import ContentCandidate
from .models import ContentItem, ContentLink, ContentType, LinkType
from .validation import PluginOutputError, normalize_http_url


class NotFoundError(Exception):
    pass


def _is_ancestor(ancestor: ContentItem, item: ContentItem) -> bool:
    seen: set[UUID] = set()
    current = item.parent
    while current is not None and current.id not in seen:
        if current.id == ancestor.id:
            return True
        seen.add(current.id)
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

    locked: dict[UUID, ContentItem] = {}
    for item_id in sorted({target_id, source_id}, key=str):
        item = ContentItem.objects.select_for_update().filter(id=item_id).first()
        if item is not None:
            locked[item.id] = item
    target = locked.get(target_id)
    source = locked.get(source_id)
    if target is None or source is None:
        raise NotFoundError("target or source content item does not exist")

    if _is_ancestor(target, source) or _is_ancestor(source, target):
        raise ValueError("items in the same hierarchy branch cannot be merged")

    ContentItem.objects.filter(parent=source).update(
        parent=target,
        revision=F("revision") + 1,
        updated_at=timezone.now(),
    )
    ContentLink.objects.filter(content_item=source).update(content_item=target)
    source.consumption_history.update(content_item=target)

    merged_metadata = dict(source.metadata)
    merged_metadata.update(target.metadata)
    target.metadata = merged_metadata
    target.revision += 1
    target.save(update_fields=["metadata", "revision", "updated_at"])

    source.delete()
    return target


def _find_link(url: str) -> ContentLink | None:
    return ContentLink.objects.select_related("content_item").filter(url=url).first()


def _update_existing_item(
    link: ContentLink,
    candidate: ContentCandidate,
    title: str,
) -> None:
    item = ContentItem.objects.select_for_update().get(pk=link.content_item_id)
    item.title = title
    item.content_type = candidate.content_type
    item.published_at = candidate.published_at
    item.duration_seconds = candidate.duration_seconds
    item.metadata = {**item.metadata, **candidate.metadata}
    item.revision += 1
    item.save(
        update_fields=[
            "title",
            "content_type",
            "published_at",
            "duration_seconds",
            "metadata",
            "revision",
            "updated_at",
        ]
    )
    link.metadata = {**link.metadata, **candidate.metadata}
    link.save(update_fields=["metadata"])


@transaction.atomic
def import_candidates(candidates: Iterable[ContentCandidate]) -> tuple[int, int]:
    created = 0
    updated = 0

    for candidate in candidates:
        title = candidate.title.strip()
        if not title:
            raise PluginOutputError("candidate title must not be empty")
        if candidate.content_type not in ContentType.values:
            raise PluginOutputError("unsupported content type")

        try:
            url = normalize_http_url(candidate.url)
        except ValueError as exc:
            raise PluginOutputError(str(exc)) from exc

        link = _find_link(url)
        if link is not None:
            _update_existing_item(link, candidate, title)
            updated += 1
            continue

        try:
            with transaction.atomic():
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
        except IntegrityError:
            link = ContentLink.objects.select_related("content_item").filter(url=url).first()
            if link is None:
                raise
            _update_existing_item(link, candidate, title)
            updated += 1

    return created, updated
