from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class ContentCandidate:
    source: str
    external_id: str
    title: str
    content_type: str
    source_url: str
    published_at: datetime | None = None
    duration_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    def fetch(self) -> list[ContentCandidate]:
        """Return source metadata without downloading or owning media files."""
        ...
