from importlib.metadata import EntryPoint, entry_points

from pydantic import BaseModel

from content_tracker_plugin_api import PLUGIN_API_VERSION, SourceAdapter

ENTRY_POINT_GROUP = "content_tracker.adapters"


class AdapterRegistryError(ValueError):
    pass


def discover_adapters() -> dict[str, EntryPoint]:
    return {entry_point.name: entry_point for entry_point in entry_points(group=ENTRY_POINT_GROUP)}


def load_adapter(adapter_key: str) -> type[SourceAdapter]:
    entry_point = discover_adapters().get(adapter_key)
    if entry_point is None:
        raise AdapterRegistryError(f'adapter "{adapter_key}" is not installed')

    adapter_class = entry_point.load()
    if getattr(adapter_class, "api_version", None) != PLUGIN_API_VERSION:
        raise AdapterRegistryError(
            f'adapter "{adapter_key}" does not support plugin API v{PLUGIN_API_VERSION}'
        )

    config_model = getattr(adapter_class, "config_model", None)
    if not isinstance(config_model, type) or not issubclass(config_model, BaseModel):
        raise AdapterRegistryError(f'adapter "{adapter_key}" has no valid config_model')

    if not callable(getattr(adapter_class, "fetch", None)):
        raise AdapterRegistryError(f'adapter "{adapter_key}" has no fetch method')

    return adapter_class
