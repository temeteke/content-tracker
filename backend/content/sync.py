from dataclasses import dataclass

from django.utils import timezone

from content_tracker_plugin_api import SyncContext

from .adapters.registry import load_adapter
from .models import SourceState
from .services import import_candidates
from .source_config import SourceDefinition


@dataclass(frozen=True)
class SyncOutcome:
    source_key: str
    created: int
    updated: int


def sync_source(source: SourceDefinition) -> SyncOutcome:
    adapter_class = load_adapter(source.adapter)
    config = adapter_class.config_model.model_validate(source.config)
    adapter = adapter_class()

    state, _ = SourceState.objects.get_or_create(source_key=source.key)
    context = SyncContext(
        source_key=source.key,
        config=config,
        state=dict(state.sync_state),
    )

    try:
        result = adapter.fetch(context)
        created, updated = import_candidates(result.candidates)
    except Exception as exc:
        state.last_error = f"{type(exc).__name__}: {exc}"
        state.save(update_fields=["last_error", "updated_at"])
        raise

    state.sync_state = dict(result.next_state)
    state.last_synced_at = timezone.now()
    state.last_error = ""
    state.save(
        update_fields=[
            "sync_state",
            "last_synced_at",
            "last_error",
            "updated_at",
        ]
    )
    return SyncOutcome(source_key=source.key, created=created, updated=updated)
