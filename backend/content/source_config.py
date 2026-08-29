from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class SourceConfigError(ValueError):
    pass


class SourceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    adapter: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class SourcesDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    api_version: Literal["content-tracker/v1"] = Field(alias="apiVersion")
    sources: list[SourceDefinition] = Field(default_factory=list)

    @field_validator("sources")
    @classmethod
    def source_keys_must_be_unique(
        cls,
        sources: list[SourceDefinition],
    ) -> list[SourceDefinition]:
        keys = [source.key for source in sources]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise ValueError(f"duplicate source keys: {', '.join(duplicates)}")
        return sources


def load_sources_file(path: str | Path) -> SourcesDocument:
    source_path = Path(path)
    try:
        raw = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SourceConfigError(f"cannot read sources file: {source_path}") from exc
    except yaml.YAMLError as exc:
        raise SourceConfigError(f"invalid YAML in sources file: {source_path}") from exc

    if raw is None:
        raw = {}

    try:
        return SourcesDocument.model_validate(raw)
    except ValidationError as exc:
        raise SourceConfigError(f"invalid sources file {source_path}: {exc}") from exc
