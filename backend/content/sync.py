from dataclasses import dataclass

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from content_tracker_plugin_api import SyncContext

from .adapters.registry import AdapterRegistryError, load_adapter
from .models import SourceState
from .services import import_candidates
from .source_config import SourceDefinition
from .validation import (
    PluginOutputError,
    describe_error,
    describe_host_error,
    validate_sync_result,
)


class SyncConflict(RuntimeError):
    def __init__(self, source_key: str) -> None:
        super().__init__(
            f'source "{source_key}" was synchronized concurrently; result discarded'
        )
        self.source_key = source_key


@dataclass(frozen=True)
class SyncOutcome:
    source_key: str
    created: int
    updated: int


def _record_error(state: SourceState, revision: int, summary: str) -> None:
    SourceState.objects.filter(pk=state.pk, revision=revision).update(
        last_error=summary,
        updated_at=timezone.now(),
    )


def sync_source(source: SourceDefinition) -> SyncOutcome:
    state, _ = SourceState.objects.get_or_create(source_key=source.key)
    snapshot_revision = state.revision

    try:
        adapter_class = load_adapter(source.adapter)
    except AdapterRegistryError as exc:
        _record_error(state, snapshot_revision, describe_host_error(exc))
        raise
    except Exception as exc:
        # entry_point.load() executes third-party import-time code.
        _record_error(state, snapshot_revision, describe_error(exc))
        raise

    try:
        config = adapter_class.config_model.model_validate(source.config)
        adapter = adapter_class()
        context = SyncContext(
            source_key=source.key,
            config=config,
            state=dict(state.sync_state),
        )
        result = adapter.fetch(context)
    except Exception as exc:
        _record_error(state, snapshot_revision, describe_error(exc))
        raise

    try:
        validated = validate_sync_result(result)
    except Exception as exc:
        _record_error(state, snapshot_revision, describe_host_error(exc))
        raise

    try:
        with transaction.atomic():
            locked = SourceState.objects.filter(
                pk=state.pk,
                revision=snapshot_revision,
            ).update(
                sync_state=validated.next_state,
                last_synced_at=timezone.now(),
                last_error="",
                revision=F("revision") + 1,
                updated_at=timezone.now(),
            )
            if locked != 1:
                raise SyncConflict(source.key)

            created, updated = import_candidates(validated.candidates)
    except SyncConflict:
        raise
    except PluginOutputError as exc:
        # Host validation/import checks raise fixed, value-free messages.
        _record_error(state, snapshot_revision, describe_host_error(exc))
        raise
    except Exception as exc:
        # Database errors and anything unexpected may embed values; record the type only.
        _record_error(state, snapshot_revision, describe_error(exc))
        raise

    return SyncOutcome(source_key=source.key, created=created, updated=updated)
