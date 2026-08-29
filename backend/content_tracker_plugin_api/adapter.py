from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Protocol

from pydantic import BaseModel

PLUGIN_API_VERSION = 1


@dataclass(frozen=True)
class ContentCandidate:
    title: str
    content_type: str
    url: str
    published_at: datetime | None = None
    duration_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SyncContext:
    source_key: str
    config: BaseModel
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SyncResult:
    candidates: list[ContentCandidate]
    next_state: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    api_version: ClassVar[int]
    config_model: ClassVar[type[BaseModel]]

    def fetch(self, context: SyncContext) -> SyncResult:
        """Fetch metadata and return content candidates without touching the host database."""
        ...
