from datetime import datetime
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError

from .models import ConsumptionHistory, ConsumptionStatus, ContentItem, ContentType

api = NinjaAPI(title="content-tracker API", version="0.1.0")


class ContentItemIn(Schema):
    title: str
    content_type: ContentType = ContentType.OTHER
    parent_id: UUID | None = None
    status: ConsumptionStatus = ConsumptionStatus.PLANNED
    description: str = ""


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


class ConsumptionHistoryIn(Schema):
    consumed_at: datetime
    rating: int | None = None
    comment: str = ""


class ConsumptionHistoryOut(Schema):
    id: UUID
    content_item_id: UUID
    consumed_at: datetime
    rating: int | None
    comment: str
    created_at: datetime


@api.get("/health")
def health(request):
    return {"status": "ok"}


@api.get("/items", response=list[ContentItemOut])
def list_items(request, content_type: ContentType | None = None,
               status: ConsumptionStatus | None = None):
    items = ContentItem.objects.all()
    if content_type is not None:
        items = items.filter(content_type=content_type)
    if status is not None:
        items = items.filter(status=status)
    return items


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


@api.get("/items/{item_id}/history", response=list[ConsumptionHistoryOut])
def list_history(request, item_id: UUID):
    return get_object_or_404(ContentItem, id=item_id).consumption_history.all()


@api.post("/items/{item_id}/history", response={201: ConsumptionHistoryOut})
def add_history(request, item_id: UUID, payload: ConsumptionHistoryIn):
    item = get_object_or_404(ContentItem, id=item_id)
    if payload.rating is not None and not 1 <= payload.rating <= 5:
        raise HttpError(422, "rating must be between 1 and 5")
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
