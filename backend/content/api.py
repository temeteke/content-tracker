from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from pydantic import AnyHttpUrl, Field, field_validator

from .models import (
    ConsumptionHistory,
    ConsumptionStatus,
    ContentItem,
    ContentLink,
    ContentType,
    LinkType,
)
from .services import merge_content_items, validate_parent_assignment

api = NinjaAPI(title="content-tracker API", version="0.5.0")

Title = Annotated[str, Field(min_length=1, max_length=500)]


class ContentItemIn(Schema):
    title: Title
    content_type: ContentType = ContentType.OTHER
    parent_id: UUID | None = None
    status: ConsumptionStatus = ConsumptionStatus.PLANNED
    description: str = ""


class ContentItemPatch(Schema):
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
    created_at: datetime
    updated_at: datetime


class ContentLinkIn(Schema):
    url: AnyHttpUrl
    link_type: LinkType = LinkType.SOURCE


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


class MergeIn(Schema):
    source_item_id: UUID


@api.get("/health")
def health(request):
    return {"status": "ok"}


@api.get("/items", response=list[ContentItemOut])
def list_items(
    request,
    content_type: ContentType | None = None,
    status: ConsumptionStatus | None = None,
    query: str | None = None,
):
    items = ContentItem.objects.all()
    if content_type is not None:
        items = items.filter(content_type=content_type)
    if status is not None:
        items = items.filter(status=status)
    if query:
        items = items.filter(title__icontains=query.strip())
    return items


@api.post("/items", response={201: ContentItemOut})
def create_item(request, payload: ContentItemIn):
    parent = get_object_or_404(ContentItem, id=payload.parent_id) if payload.parent_id else None
    item = ContentItem.objects.create(
        title=payload.title.strip(),
        content_type=payload.content_type,
        parent=parent,
        status=payload.status,
        description=payload.description,
    )
    return 201, item


@api.get("/items/{item_id}", response=ContentItemOut)
def get_item(request, item_id: UUID):
    return get_object_or_404(ContentItem, id=item_id)


@api.patch("/items/{item_id}", response=ContentItemOut)
def update_item(request, item_id: UUID, payload: ContentItemPatch):
    item = get_object_or_404(ContentItem, id=item_id)
    fields = payload.model_fields_set

    if "title" in fields and payload.title is not None:
        item.title = payload.title.strip()
    if "content_type" in fields and payload.content_type is not None:
        item.content_type = payload.content_type
    if "status" in fields and payload.status is not None:
        item.status = payload.status
    if "description" in fields and payload.description is not None:
        item.description = payload.description
    if "parent_id" in fields:
        parent = (
            get_object_or_404(ContentItem, id=payload.parent_id)
            if payload.parent_id
            else None
        )
        try:
            validate_parent_assignment(item, parent)
        except ValueError as exc:
            raise HttpError(422, str(exc)) from exc
        item.parent = parent

    item.save()
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
            url=str(payload.url),
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


@api.post("/items/{item_id}/history", response={201: ConsumptionHistoryOut})
def add_history(request, item_id: UUID, payload: ConsumptionHistoryIn):
    item = get_object_or_404(ContentItem, id=item_id)
    history = ConsumptionHistory.objects.create(
        content_item=item,
        consumed_at=payload.consumed_at,
        rating=payload.rating,
        comment=payload.comment,
    )
    if item.status != ConsumptionStatus.COMPLETED:
        item.status = ConsumptionStatus.COMPLETED
        item.save(update_fields=["status", "updated_at"])
    return 201, history


@api.post("/items/{item_id}/merge", response=ContentItemOut)
def merge_item(request, item_id: UUID, payload: MergeIn):
    try:
        return merge_content_items(
            target_id=item_id,
            source_id=payload.source_item_id,
        )
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc
