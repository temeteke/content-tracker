from datetime import datetime, timezone

import pytest

from content.adapters.base import ContentCandidate
from content.models import ConsumptionHistory, ContentItem, ContentLink, ContentType
from content.services import import_candidates, merge_content_items


@pytest.mark.django_db
def test_import_candidates_is_idempotent_by_source_external_id():
    candidate = ContentCandidate(
        source="example",
        external_id="episode-1",
        title="Episode 1",
        content_type=ContentType.PODCAST,
        source_url="https://example.invalid/episode-1",
    )

    assert import_candidates([candidate]) == (1, 0)
    assert import_candidates([candidate]) == (0, 1)
    assert ContentItem.objects.count() == 1
    assert ContentLink.objects.count() == 1


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
        consumed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    merge_content_items(target_id=target.id, source_id=source.id)

    child.refresh_from_db()
    link.refresh_from_db()
    history.refresh_from_db()

    assert child.parent == target
    assert link.content_item == target
    assert history.content_item == target
    assert not ContentItem.objects.filter(id=source.id).exists()
