from io import StringIO

import pytest
from django.core.management import call_command

from content.adapters.base import ContentCandidate
from content.models import ContentItem, ContentType


class FakeAdapter:
    def fetch(self):
        return [
            ContentCandidate(
                source="test-source",
                external_id="item-1",
                title="Imported item",
                content_type=ContentType.RADIO,
                source_url="https://example.invalid/imported-item",
            )
        ]


@pytest.mark.django_db
def test_sync_content_management_command():
    output = StringIO()

    call_command(
        "sync_content",
        "content.tests.test_management.FakeAdapter",
        stdout=output,
    )

    assert ContentItem.objects.filter(title="Imported item").exists()
    assert "created=1 updated=0" in output.getvalue()
