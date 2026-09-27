from datetime import UTC, datetime, timedelta

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
    body = created.json()
    item_id = body["id"]
    assert body["revision"] == 1

    ContentItem.objects.create(
        title="Unrelated Video",
        content_type="video",
        status="active",
    )

    searched = client.get(
        "/items",
        query_params={"query": "radio", "status": "planned"},
    )
    assert searched.status_code == 200
    assert [item["id"] for item in searched.json()] == [item_id]

    updated = client.patch(
        f"/items/{item_id}",
        json={"status": "active", "revision": body["revision"]},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "active"
    assert updated.json()["revision"] == 2


@pytest.mark.django_db
def test_list_items_paginates_with_limit_and_offset():
    for index in range(5):
        ContentItem.objects.create(title=f"Item {index}")

    first = client.get("/items", query_params={"limit": 2, "offset": 0})
    second = client.get("/items", query_params={"limit": 2, "offset": 2})
    beyond = client.get("/items", query_params={"limit": 2, "offset": 10})

    assert first.status_code == 200
    assert len(first.json()) == 2
    assert len(second.json()) == 2
    assert {item["id"] for item in first.json()}.isdisjoint(
        {item["id"] for item in second.json()}
    )
    assert beyond.json() == []


@pytest.mark.django_db
@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 501}, {"offset": -1}])
def test_list_items_rejects_invalid_paging(params):
    assert client.get("/items", query_params=params).status_code == 422


@pytest.mark.django_db
def test_empty_title_is_rejected():
    response = client.post(
        "/items",
        json={"title": "", "content_type": "video"},
    )

    assert response.status_code == 422


@pytest.mark.django_db
def test_whitespace_only_title_is_rejected():
    assert client.post("/items", json={"title": "   "}).status_code == 422

    item = ContentItem.objects.create(title="Existing")
    patched = client.patch(
        f"/items/{item.id}",
        json={"title": "   ", "revision": item.revision},
    )
    assert patched.status_code == 422


@pytest.mark.django_db
def test_patch_requires_revision_and_detects_conflicts():
    created = client.post("/items", json={"title": "Concurrent"})
    item_id = created.json()["id"]

    missing = client.patch(f"/items/{item_id}", json={"status": "active"})
    assert missing.status_code == 422

    stale = client.patch(
        f"/items/{item_id}",
        json={"status": "active", "revision": 99},
    )
    assert stale.status_code == 409

    current = client.get(f"/items/{item_id}").json()["revision"]
    accepted = client.patch(
        f"/items/{item_id}",
        json={"status": "active", "revision": current},
    )
    assert accepted.status_code == 200


@pytest.mark.django_db
def test_patch_rejects_explicit_null_for_non_nullable_fields():
    item = ContentItem.objects.create(title="Nullable")

    for field in ("title", "content_type", "status", "description"):
        response = client.patch(
            f"/items/{item.id}",
            json={field: None, "revision": item.revision},
        )
        assert response.status_code == 422, field


@pytest.mark.django_db
def test_patch_updates_only_provided_fields():
    item = ContentItem.objects.create(title="Original", description="keep me")

    response = client.patch(
        f"/items/{item.id}",
        json={"status": "active", "revision": item.revision},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Original"
    assert response.json()["description"] == "keep me"


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
    assert item.revision == 2


@pytest.mark.django_db
def test_consumption_history_requires_timezone_and_non_future_date():
    item = ContentItem.objects.create(title="Episode")

    naive = client.post(
        f"/items/{item.id}/history",
        json={"consumed_at": "2026-08-01T12:00:00"},
    )
    assert naive.status_code == 422

    future = client.post(
        f"/items/{item.id}/history",
        json={
            "consumed_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert future.status_code == 422


@pytest.mark.django_db
def test_hierarchy_cycle_is_rejected():
    parent = ContentItem.objects.create(title="Parent")
    child = ContentItem.objects.create(title="Child", parent=parent)

    response = client.patch(
        f"/items/{parent.id}",
        json={"parent_id": str(child.id), "revision": parent.revision},
    )

    assert response.status_code == 422


@pytest.mark.django_db
def test_patch_prefers_conflict_over_invalid_parent():
    parent = ContentItem.objects.create(title="Parent")
    child = ContentItem.objects.create(title="Child", parent=parent)

    response = client.patch(
        f"/items/{parent.id}",
        json={"parent_id": str(child.id), "revision": parent.revision + 1},
    )

    assert response.status_code == 409


@pytest.mark.django_db
def test_patch_missing_parent_returns_not_found():
    item = ContentItem.objects.create(title="Child")

    response = client.patch(
        f"/items/{item.id}",
        json={
            "parent_id": "00000000-0000-0000-0000-000000000000",
            "revision": item.revision,
        },
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_patch_without_fields_returns_unprocessable():
    item = ContentItem.objects.create(title="Noop")

    response = client.patch(f"/items/{item.id}", json={"revision": item.revision})

    assert response.status_code == 422


@pytest.mark.django_db
def test_merge_missing_source_returns_not_found():
    target = ContentItem.objects.create(title="Target")

    response = client.post(
        f"/items/{target.id}/merge",
        json={"source_item_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_content_link_is_globally_unique_and_requires_http_url():
    first = ContentItem.objects.create(title="First")
    second = ContentItem.objects.create(title="Second")
    payload = {"url": "https://example.invalid/content"}

    assert client.post(f"/items/{first.id}/links", json=payload).status_code == 201
    assert client.post(f"/items/{second.id}/links", json=payload).status_code == 409

    invalid = client.post(
        f"/items/{second.id}/links",
        json={"url": "not-a-url"},
    )
    assert invalid.status_code == 422


@pytest.mark.django_db
def test_content_link_preserves_url_identity_without_implicit_normalization():
    item = ContentItem.objects.create(title="Identity")

    created = client.post(
        f"/items/{item.id}/links",
        json={"url": "https://example.invalid"},
    )

    assert created.status_code == 201
    assert created.json()["url"] == "https://example.invalid"
