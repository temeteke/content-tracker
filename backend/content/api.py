from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from django.db import IntegrityError, connection, transaction
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import NinjaAPI, Query, Schema
from ninja.errors import HttpError
from pydantic import BeforeValidator, Field, field_validator

from .models import (
    ConsumptionHistory,
    ConsumptionStatus,
    ContentItem,
    ContentLink,
    ContentType,
    LinkType,
)
from .services import NotFoundError, merge_content_items, validate_parent_assignment
from .validation import MAX_URL_LENGTH, normalize_http_url

api = NinjaAPI(title="content-tracker API", version="0.6.0")


def _strip(value):
    return value.strip() if isinstance(value, str) else value


Title = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=500)]


class ContentItemIn(Schema):
    title: Title
    content_type: ContentType = ContentType.OTHER
    parent_id: UUID | None = None
    status: ConsumptionStatus = ConsumptionStatus.PLANNED
    description: str = ""


class ContentItemPatch(Schema):
    revision: int
    title: Title | None = None
    content_type: ContentType | None = None
    parent_id: UUID | None = None
    status: ConsumptionStatus | None = None
    description: str | None = None


class ContentItemOut(Schema):
    id: UUID
    title: str
    content_type: str
    parent_id: UUID | None
    status: str
    description: str
    published_at: datetime | None
    duration_seconds: int | None
    revision: int
    created_at: datetime
    updated_at: datetime


class ContentLinkIn(Schema):
    url: Annotated[str, Field(min_length=1, max_length=MAX_URL_LENGTH)]
    link_type: LinkType = LinkType.SOURCE

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        try:
            return normalize_http_url(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class ContentLinkOut(Schema):
    id: UUID
    content_item_id: UUID
    url: str
    link_type: str
    created_at: datetime


class ConsumptionHistoryIn(Schema):
    consumed_at: datetime
    rating: Annotated[int, Field(ge=1, le=5)] | None = None
    comment: str = ""

    @field_validator("consumed_at")
    @classmethod
    def validate_consumed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("consumed_at must include a timezone")
        if value > datetime.now(UTC):
            raise ValueError("consumed_at cannot be in the future")
        return value


class ConsumptionHistoryOut(Schema):
    id: UUID
    content_item_id: UUID
    consumed_at: datetime
    rating: int | None
    comment: str
    created_at: datetime


class ConsumptionHistoryPatch(Schema):
    consumed_at: datetime | None = None
    rating: Annotated[int, Field(ge=1, le=5)] | None = None
    comment: str | None = None

    @field_validator("consumed_at")
    @classmethod
    def validate_consumed_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("consumed_at must include a timezone")
        if value > datetime.now(UTC):
            raise ValueError("consumed_at cannot be in the future")
        return value


class MergeIn(Schema):
    source_item_id: UUID


def _lock_items(*item_ids: UUID | None) -> dict[UUID, ContentItem]:
    ids = sorted({item_id for item_id in item_ids if item_id is not None}, key=str)
    locked: dict[UUID, ContentItem] = {}
    for item_id in ids:
        item = ContentItem.objects.select_for_update().filter(id=item_id).first()
        if item is not None:
            locked[item.id] = item
    return locked


@api.get("/health")
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as exc:
        raise HttpError(503, "database is unavailable") from exc
    return {"status": "ok"}


@api.get("/items", response=list[ContentItemOut])
def list_items(
    request,
    response: HttpResponse,
    content_type: ContentType | None = None,
    status: ConsumptionStatus | None = None,
    query: str | None = None,
    parent_id: UUID | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    items = ContentItem.objects.all()
    if content_type is not None:
        items = items.filter(content_type=content_type)
    if status is not None:
        items = items.filter(status=status)
    if query:
        items = items.filter(title__icontains=query.strip())
    if parent_id is not None:
        items = items.filter(parent_id=parent_id)
    total = items.count()
    response["X-Total-Count"] = str(total)
    return items[offset : offset + limit]


@api.post("/items", response={201: ContentItemOut})
def create_item(request, payload: ContentItemIn):
    parent = get_object_or_404(ContentItem, id=payload.parent_id) if payload.parent_id else None
    item = ContentItem.objects.create(
        title=payload.title,
        content_type=payload.content_type,
        parent=parent,
        status=payload.status,
        description=payload.description,
    )
    return 201, item


@api.get("/items/{item_id}", response=ContentItemOut)
def get_item(request, item_id: UUID):
    return get_object_or_404(ContentItem, id=item_id)


@api.delete("/items/{item_id}", response={204: None})
def delete_item(request, item_id: UUID, revision: int = Query(..., ge=1)):
    with transaction.atomic():
        item = ContentItem.objects.select_for_update().filter(id=item_id).first()
        if item is None:
            raise HttpError(404, "content item not found")
        if item.revision != revision:
            raise HttpError(409, "content item was modified by another request")
        ContentItem.objects.filter(parent=item).update(
            parent=None,
            revision=F("revision") + 1,
            updated_at=timezone.now(),
        )
        item.delete()
    return 204, None


@api.patch("/items/{item_id}", response=ContentItemOut)
def update_item(request, item_id: UUID, payload: ContentItemPatch):
    existing = get_object_or_404(ContentItem, id=item_id)
    fields = payload.model_fields_set

    for name in ("title", "content_type", "status", "description"):
        if name in fields and getattr(payload, name) is None:
            raise HttpError(422, f"{name} must not be null")

    updates = {}
    for name in ("title", "content_type", "status", "description"):
        if name in fields:
            updates[name] = getattr(payload, name)

    with transaction.atomic():
        lock_ids = [existing.id]
        if "parent_id" in fields and payload.parent_id is not None:
            lock_ids.append(payload.parent_id)

        locked = _lock_items(*lock_ids)
        item = locked.get(existing.id)
        if item is None:
            raise HttpError(404, "content item not found")

        if item.revision != payload.revision:
            raise HttpError(409, "content item was modified by another request")

        if "parent_id" in fields:
            if payload.parent_id is None:
                parent = None
            else:
                parent = locked.get(payload.parent_id)
                if parent is None:
                    raise HttpError(404, "parent content item not found")
            try:
                validate_parent_assignment(item, parent)
            except ValueError as exc:
                raise HttpError(422, str(exc)) from exc
            updates["parent"] = parent

        if not updates:
            raise HttpError(422, "no updatable fields were provided")

        updated = ContentItem.objects.filter(
            pk=item.id,
            revision=payload.revision,
        ).update(
            **updates,
            revision=F("revision") + 1,
            updated_at=timezone.now(),
        )
        if updated == 0:
            raise HttpError(409, "content item was modified by another request")

    item.refresh_from_db()
    return item


@api.get("/items/{item_id}/links", response=list[ContentLinkOut])
def list_links(request, item_id: UUID):
    return get_object_or_404(ContentItem, id=item_id).links.all()


@api.post("/items/{item_id}/links", response={201: ContentLinkOut})
def add_link(request, item_id: UUID, payload: ContentLinkIn):
    item = get_object_or_404(ContentItem, id=item_id)
    try:
        link = ContentLink.objects.create(
            content_item=item,
            url=payload.url,
            link_type=payload.link_type,
        )
    except IntegrityError as exc:
        raise HttpError(409, "link already exists") from exc
    return 201, link


@api.delete("/links/{link_id}", response={204: None})
def delete_link(request, link_id: UUID):
    get_object_or_404(ContentLink, id=link_id).delete()
    return 204, None


@api.get("/items/{item_id}/history", response=list[ConsumptionHistoryOut])
def list_history(request, item_id: UUID):
    return get_object_or_404(ContentItem, id=item_id).consumption_history.all()


@api.get("/history/{history_id}", response=ConsumptionHistoryOut)
def get_history(request, history_id: UUID):
    return get_object_or_404(ConsumptionHistory, id=history_id)


@api.patch("/history/{history_id}", response=ConsumptionHistoryOut)
def update_history(request, history_id: UUID, payload: ConsumptionHistoryPatch):
    fields = payload.model_fields_set
    updates = {}
    for name in ("consumed_at", "rating", "comment"):
        if name in fields:
            updates[name] = getattr(payload, name)

    if not updates:
        raise HttpError(422, "no updatable fields were provided")

    with transaction.atomic():
        history = (
            ConsumptionHistory.objects.select_for_update()
            .select_related("content_item")
            .filter(id=history_id)
            .first()
        )
        if history is None:
            raise HttpError(404, "consumption history not found")
        for name, value in updates.items():
            setattr(history, name, value)
        history.save(update_fields=list(updates))
        ContentItem.objects.filter(pk=history.content_item_id).update(
            revision=F("revision") + 1,
            updated_at=timezone.now(),
        )
    history.refresh_from_db()
    return history


@api.delete("/history/{history_id}", response={204: None})
def delete_history(request, history_id: UUID):
    with transaction.atomic():
        history = (
            ConsumptionHistory.objects.select_for_update()
            .filter(id=history_id)
            .first()
        )
        if history is None:
            raise HttpError(404, "consumption history not found")
        item_id = history.content_item_id
        history.delete()
        ContentItem.objects.filter(pk=item_id).update(
            revision=F("revision") + 1,
            updated_at=timezone.now(),
        )
    return 204, None


@api.post("/items/{item_id}/history", response={201: ConsumptionHistoryOut})
def add_history(request, item_id: UUID, payload: ConsumptionHistoryIn):
    item = get_object_or_404(ContentItem, id=item_id)
    with transaction.atomic():
        history = ConsumptionHistory.objects.create(
            content_item=item,
            consumed_at=payload.consumed_at,
            rating=payload.rating,
            comment=payload.comment,
        )
        if item.status != ConsumptionStatus.COMPLETED:
            ContentItem.objects.filter(pk=item.id).update(
                status=ConsumptionStatus.COMPLETED,
                revision=F("revision") + 1,
                updated_at=timezone.now(),
            )
    return 201, history


@api.post("/items/{item_id}/merge", response=ContentItemOut)
def merge_item(request, item_id: UUID, payload: MergeIn):
    try:
        return merge_content_items(
            target_id=item_id,
            source_id=payload.source_item_id,
        )
    except NotFoundError as exc:
        raise HttpError(404, str(exc)) from exc
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc
