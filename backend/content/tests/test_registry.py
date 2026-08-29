from importlib.metadata import EntryPoint

import pytest
from pydantic import BaseModel

from content.adapters import registry
from content.adapters.registry import AdapterRegistryError
from content_tracker_plugin_api import PLUGIN_API_VERSION, SyncResult


class Config(BaseModel):
    value: str


class GoodAdapter:
    api_version = PLUGIN_API_VERSION
    config_model = Config

    def fetch(self, context):
        return SyncResult(candidates=[])


class OldAdapter:
    api_version = 0
    config_model = Config

    def fetch(self, context):
        return SyncResult(candidates=[])


def _entry_point(value: str) -> EntryPoint:
    return EntryPoint(name="test", value=value, group=registry.ENTRY_POINT_GROUP)


def test_load_adapter(monkeypatch):
    entry = _entry_point("content.tests.test_registry:GoodAdapter")
    monkeypatch.setattr(registry, "discover_adapters", lambda: {"test": entry})

    assert registry.load_adapter("test") is GoodAdapter


def test_load_adapter_rejects_incompatible_api(monkeypatch):
    entry = _entry_point("content.tests.test_registry:OldAdapter")
    monkeypatch.setattr(registry, "discover_adapters", lambda: {"test": entry})

    with pytest.raises(AdapterRegistryError, match="plugin API"):
        registry.load_adapter("test")
