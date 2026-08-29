from io import StringIO

import pytest
from django.core.management import call_command
from pydantic import BaseModel

from content import sync
from content.models import ContentItem, ContentType
from content_tracker_plugin_api import (
    PLUGIN_API_VERSION,
    ContentCandidate,
    SyncResult,
)


class FakeConfig(BaseModel):
    feed_url: str


class FakeAdapter:
    api_version = PLUGIN_API_VERSION
    config_model = FakeConfig

    def fetch(self, context):
        return SyncResult(
            candidates=[
                ContentCandidate(
                    title="Imported item",
                    content_type=ContentType.RADIO,
                    url="https://example.invalid/imported-item",
                )
            ]
        )


@pytest.mark.django_db
def test_sync_content_management_command(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "load_adapter", lambda adapter_key: FakeAdapter)
    sources_file = tmp_path / "sources.yaml"
    sources_file.write_text(
        """
apiVersion: content-tracker/v1
sources:
  - key: test-source
    adapter: fake
    config:
      feed_url: https://example.org/feed.xml
""".strip(),
        encoding="utf-8",
    )
    output = StringIO()

    call_command(
        "sync_content",
        "--sources-file",
        str(sources_file),
        stdout=output,
    )

    assert ContentItem.objects.filter(title="Imported item").exists()
    assert "test-source: created=1 updated=0" in output.getvalue()
