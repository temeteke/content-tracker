from datetime import UTC, datetime

import pytest
from ninja.testing import TestClient

from content.api import api
from content.models import ConsumptionStatus, ContentItem

client = TestClient(api)


@pytest.mark.django_db
def test_create_search_and_update_content_item():
    created = client.post(
        "/items",
        json={"title": "Example Radio Program", "content_type": "radio"},
    )
    assert created.status_code == 201
    item_id = created.json()["id"]

    searched = client.get("/items", params={"query": "radio", "status": "planned"})
    assert searched.status_code == 200
    assert [item["id"] for item in searched.json()] == [item_id]

    updated = client.patch(
        f"/items/{item_id}",
        json={"status": "active"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "active"


@pytest.mark.django_db
def test_consumption_history_marks_item_completed():
    item = ContentItem.objects.create(title="Episode")

    response = client.post(
        f"/items/{item.id}/history",
        json={
            "consumed_at": datetime(2026, 8, 1, 12, 0, tzinfo=UTC).isoformat(),
            "rating": 4,
        },
    )

    assert response.status_code == 201
    item.refresh_from_db()
    assert item.status == ConsumptionStatus.COMPLETED


@pytest.mark.django_db
def test_hierarchy_cycle_is_rejected():
    parent = ContentItem.objects.create(title="Parent")
    child = ContentItem.objects.create(title="Child", parent=parent)

    response = client.patch(
        f"/items/{parent.id}",
        json={"parent_id": str(child.id)},
    )

    assert response.status_code == 422


@pytest.mark.django_db
def test_content_link_is_globally_unique():
    first = ContentItem.objects.create(title="First")
    second = ContentItem.objects.create(title="Second")
    payload = {"url": "https://example.invalid/content"}

    assert client.post(f"/items/{first.id}/links", json=payload).status_code == 201
    assert client.post(f"/items/{second.id}/links", json=payload).status_code == 409
