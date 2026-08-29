from datetime import UTC, datetime

import pytest

from content.models import ConsumptionHistory, ContentItem, ContentType


@pytest.mark.django_db
def test_content_item_supports_arbitrary_hierarchy():
    series = ContentItem.objects.create(title="Example series", content_type=ContentType.PODCAST)
    episode = ContentItem.objects.create(
        title="Episode 1",
        content_type=ContentType.PODCAST,
        parent=series,
    )

    assert episode.parent == series
    assert list(series.children.all()) == [episode]


@pytest.mark.django_db
def test_multiple_consumption_history_entries_are_preserved():
    item = ContentItem.objects.create(title="Example", content_type=ContentType.VIDEO)
    first = ConsumptionHistory.objects.create(
        content_item=item,
        consumed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    second = ConsumptionHistory.objects.create(
        content_item=item,
        consumed_at=datetime(2026, 2, 1, tzinfo=UTC),
        rating=5,
    )

    assert list(item.consumption_history.values_list("id", flat=True)) == [second.id, first.id]
