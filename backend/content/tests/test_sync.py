import pytest
from pydantic import BaseModel

from content import sync
from content.models import ContentItem, SourceState
from content.source_config import SourceDefinition
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
        assert context.source_key == "example"
        assert context.config.feed_url == "https://example.org/feed.xml"
        return SyncResult(
            candidates=[
                ContentCandidate(
                    title="Imported episode",
                    content_type="podcast",
                    url="https://example.org/episodes/1",
                )
            ],
            next_state={"cursor": "next"},
        )


@pytest.mark.django_db
def test_sync_source_updates_content_and_runtime_state(monkeypatch):
    monkeypatch.setattr(sync, "load_adapter", lambda adapter_key: FakeAdapter)
    source = SourceDefinition(
        key="example",
        adapter="podcast",
        config={"feed_url": "https://example.org/feed.xml"},
    )

    outcome = sync.sync_source(source)

    assert outcome.created == 1
    assert ContentItem.objects.get().title == "Imported episode"

    state = SourceState.objects.get(source_key="example")
    assert state.sync_state == {"cursor": "next"}
    assert state.last_synced_at is not None
    assert state.last_error == ""
