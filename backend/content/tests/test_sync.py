import pytest
from django.db.models import F
from pydantic import BaseModel, ValidationError, field_validator

from content import sync
from content.models import ContentItem, SourceState
from content.source_config import SourceDefinition
from content.validation import PluginOutputError
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


def _source() -> SourceDefinition:
    return SourceDefinition(
        key="example",
        adapter="podcast",
        config={"feed_url": "https://example.org/feed.xml"},
    )


@pytest.mark.django_db
def test_sync_source_updates_content_and_runtime_state(monkeypatch):
    monkeypatch.setattr(sync, "load_adapter", lambda adapter_key: FakeAdapter)

    outcome = sync.sync_source(_source())

    assert outcome.created == 1
    assert ContentItem.objects.get().title == "Imported episode"

    state = SourceState.objects.get(source_key="example")
    assert state.sync_state == {"cursor": "next"}
    assert state.last_synced_at is not None
    assert state.last_error == ""
    assert state.revision == 2


@pytest.mark.django_db
def test_sync_source_discards_result_on_concurrent_update(monkeypatch):
    class ConflictingAdapter(FakeAdapter):
        def fetch(self, context):
            SourceState.objects.filter(source_key="example").update(
                revision=F("revision") + 1
            )
            return super().fetch(context)

    monkeypatch.setattr(sync, "load_adapter", lambda adapter_key: ConflictingAdapter)

    with pytest.raises(sync.SyncConflict):
        sync.sync_source(_source())

    assert ContentItem.objects.count() == 0
    state = SourceState.objects.get(source_key="example")
    assert state.sync_state == {}
    assert state.last_error == ""


@pytest.mark.django_db
def test_sync_source_rejects_non_json_next_state(monkeypatch):
    class FailingAdapter(FakeAdapter):
        def fetch(self, context):
            result = super().fetch(context)
            return SyncResult(
                candidates=result.candidates,
                next_state={"cursor": object()},
            )

    monkeypatch.setattr(sync, "load_adapter", lambda adapter_key: FailingAdapter)

    with pytest.raises(PluginOutputError):
        sync.sync_source(_source())

    assert ContentItem.objects.count() == 0
    state = SourceState.objects.get(source_key="example")
    assert state.sync_state == {}
    assert "PluginOutputError" in state.last_error
    assert "JSON serializable" in state.last_error


@pytest.mark.django_db
def test_sync_source_rolls_back_state_when_import_fails(monkeypatch):
    def failing_import(candidates):
        raise RuntimeError("import failed")

    monkeypatch.setattr(sync, "load_adapter", lambda adapter_key: FakeAdapter)
    monkeypatch.setattr(sync, "import_candidates", failing_import)

    with pytest.raises(RuntimeError):
        sync.sync_source(_source())

    state = SourceState.objects.get(source_key="example")
    assert state.sync_state == {}
    assert state.revision == 1
    assert state.last_error == "RuntimeError"


@pytest.mark.django_db
def test_sync_source_records_load_failure(monkeypatch):
    from content.adapters.registry import AdapterRegistryError

    def raise_missing(adapter_key):
        raise AdapterRegistryError(f'adapter "{adapter_key}" is not installed')

    monkeypatch.setattr(sync, "load_adapter", raise_missing)

    with pytest.raises(AdapterRegistryError):
        sync.sync_source(_source())

    state = SourceState.objects.get(source_key="example")
    assert state.last_error == 'AdapterRegistryError: adapter "podcast" is not installed'


@pytest.mark.django_db
def test_sync_source_adapter_config_error_excludes_values(monkeypatch):
    class SecretConfig(BaseModel):
        token: str

        @field_validator("token")
        @classmethod
        def check(cls, value: str) -> str:
            if value != "ok":
                raise ValueError(f"token={value} is invalid")
            return value

    class SecretAdapter:
        api_version = PLUGIN_API_VERSION
        config_model = SecretConfig

        def fetch(self, context):
            raise AssertionError("must not be called")

    monkeypatch.setattr(sync, "load_adapter", lambda adapter_key: SecretAdapter)
    source = SourceDefinition(
        key="example",
        adapter="podcast",
        config={"token": "SENTINEL-CONFIG"},
    )

    with pytest.raises(ValidationError):
        sync.sync_source(source)

    state = SourceState.objects.get(source_key="example")
    assert state.last_error.startswith("ValidationError")
    assert "token" in state.last_error
    assert "value_error" in state.last_error
    assert "SENTINEL-CONFIG" not in state.last_error
    assert "is invalid" not in state.last_error


@pytest.mark.django_db
def test_sync_source_adapter_import_failure_records_type_only(monkeypatch):
    def raise_secret(adapter_key):
        raise RuntimeError("token=SENTINEL-IMPORT")

    monkeypatch.setattr(sync, "load_adapter", raise_secret)

    with pytest.raises(RuntimeError):
        sync.sync_source(_source())

    state = SourceState.objects.get(source_key="example")
    assert state.last_error == "RuntimeError"
    assert "SENTINEL-IMPORT" not in state.last_error
