from datetime import UTC, datetime

import pytest

from content.adapters.base import ContentCandidate
from content.models import ConsumptionHistory, ContentItem, ContentLink, ContentType
from content.services import import_candidates, merge_content_items


@pytest.mark.django_db
def test_import_candidates_is_idempotent_by_url():
    candidate = ContentCandidate(
        title="Episode 1",
        content_type=ContentType.PODCAST,
        url="https://example.invalid/episode-1",
    )

    assert import_candidates([candidate]) == (1, 0)
    assert import_candidates([candidate]) == (0, 1)
    assert ContentItem.objects.count() == 1
    assert ContentLink.objects.count() == 1


@pytest.mark.django_db
def test_import_candidates_rejects_empty_title():
    candidate = ContentCandidate(
        title=" ",
        content_type=ContentType.VIDEO,
        url="https://example.invalid/empty",
    )

    with pytest.raises(ValueError, match="title"):
        import_candidates([candidate])


@pytest.mark.django_db
def test_import_candidates_rejects_invalid_url():
    candidate = ContentCandidate(
        title="Invalid URL",
        content_type=ContentType.VIDEO,
        url="not-a-url",
    )

    with pytest.raises(ValueError, match="url"):
        import_candidates([candidate])


@pytest.mark.django_db
def test_merge_moves_links_history_and_children():
    target = ContentItem.objects.create(title="Canonical")
    source = ContentItem.objects.create(title="Duplicate")
    child = ContentItem.objects.create(title="Child", parent=source)
    link = ContentLink.objects.create(
        content_item=source,
        url="https://example.invalid/item",
    )
    history = ConsumptionHistory.objects.create(
        content_item=source,
        consumed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    merge_content_items(target_id=target.id, source_id=source.id)

    child.refresh_from_db()
    link.refresh_from_db()
    history.refresh_from_db()

    assert child.parent == target
    assert link.content_item == target
    assert history.content_item == target
    assert not ContentItem.objects.filter(id=source.id).exists()


@pytest.mark.django_db
def test_merge_rejects_items_in_same_hierarchy_branch():
    parent = ContentItem.objects.create(title="Parent")
    child = ContentItem.objects.create(title="Child", parent=parent)

    with pytest.raises(ValueError, match="hierarchy branch"):
        merge_content_items(target_id=parent.id, source_id=child.id)
