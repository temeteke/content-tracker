from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError, field_validator

from content.models import ContentType
from content.validation import (
    PluginOutputError,
    describe_error,
    describe_host_error,
    normalize_http_url,
    validate_sync_result,
)
from content_tracker_plugin_api import ContentCandidate, SyncResult


def _candidate(**overrides) -> ContentCandidate:
    values = {
        "title": "Episode",
        "content_type": ContentType.PODCAST,
        "url": "https://example.invalid/episode",
    }
    values.update(overrides)
    return ContentCandidate(**values)


def test_normalize_http_url_trims_without_rewriting():
    assert normalize_http_url("  https://example.invalid  ") == "https://example.invalid"


def test_normalize_http_url_rejects_invalid_scheme():
    with pytest.raises(ValueError):
        normalize_http_url("ftp://example.invalid")
    with pytest.raises(ValueError):
        normalize_http_url("not-a-url")


def test_validate_sync_result_normalizes_candidates():
    result = validate_sync_result(
        SyncResult(candidates=[_candidate(title="  Spaced  ")], next_state={"cursor": "x"})
    )

    assert result.candidates[0].title == "Spaced"
    assert result.next_state == {"cursor": "x"}


@pytest.mark.parametrize(
    "candidate",
    [
        _candidate(title=""),
        _candidate(title="   "),
        _candidate(title="x" * 501),
        _candidate(content_type="unknown"),
        _candidate(url="not-a-url"),
        _candidate(duration_seconds=-1),
        _candidate(published_at=datetime(2026, 1, 1)),
        _candidate(metadata={"when": datetime(2026, 1, 1, tzinfo=UTC)}),
    ],
)
def test_validate_sync_result_rejects_invalid_candidate(candidate):
    with pytest.raises(PluginOutputError):
        validate_sync_result(SyncResult(candidates=[candidate]))


def test_validate_sync_result_rejects_non_json_next_state():
    with pytest.raises(PluginOutputError):
        validate_sync_result(SyncResult(candidates=[], next_state={"cursor": object()}))


def test_validate_sync_result_rejects_nan_and_infinity():
    with pytest.raises(PluginOutputError):
        validate_sync_result(
            SyncResult(candidates=[_candidate(metadata={"score": float("nan")})])
        )
    with pytest.raises(PluginOutputError):
        validate_sync_result(SyncResult(candidates=[], next_state={"score": float("inf")}))


def test_validate_sync_result_rejects_duration_above_db_limit():
    with pytest.raises(PluginOutputError):
        validate_sync_result(SyncResult(candidates=[_candidate(duration_seconds=2**31)]))


class _SecretConfig(BaseModel):
    """Stands in for a third-party adapter config_model whose validator embeds values."""

    token: str

    @field_validator("token")
    @classmethod
    def check(cls, value: str) -> str:
        if value != "ok":
            raise ValueError(f"token={value} is invalid")
        return value


def test_describe_error_excludes_message_and_input():
    try:
        _SecretConfig(token="SENTINEL-ADAPTER")
    except ValidationError as exc:
        summary = describe_error(exc)

    assert summary.startswith("ValidationError")
    assert "token" in summary
    assert "value_error" in summary
    assert "SENTINEL-ADAPTER" not in summary
    assert "is invalid" not in summary


def test_describe_error_records_class_name_only():
    assert describe_error(RuntimeError("token=abc failed")) == "RuntimeError"
    assert describe_error(RuntimeError("https://u:secret@h/x")) == "RuntimeError"
    assert (
        describe_error(ValueError("candidate title must not be empty")) == "ValueError"
    )


def test_describe_error_truncates_long_output():
    assert len(describe_error(RuntimeError("x" * 1000))) <= 300


class _HostConfig(BaseModel):
    """Stands in for a host model whose validator messages never embed values."""

    token: str

    @field_validator("token")
    @classmethod
    def check(cls, value: str) -> str:
        if value != "ok":
            raise ValueError("token is invalid")
        return value


def test_describe_host_error_keeps_message_without_input():
    try:
        _HostConfig(token="SENTINEL-HOST")
    except ValidationError as exc:
        summary = describe_host_error(exc)

    assert summary.startswith("ValidationError")
    assert "token" in summary
    assert "is invalid" in summary
    assert "SENTINEL-HOST" not in summary


def test_describe_host_error_keeps_generic_message():
    assert describe_host_error(
        RuntimeError("candidate title must not be empty")
    ) == "RuntimeError: candidate title must not be empty"


def test_host_model_errors_never_contain_input_values():
    from content.source_config import SourcesDocument

    raw = {
        "apiVersion": "content-tracker/v1",
        "sources": [{"key": "s", "adapter": "a", "password": "SENTINEL-YAML"}],
    }
    try:
        SourcesDocument.model_validate(raw)
    except ValidationError as exc:
        summary = describe_host_error(exc)

    assert "SENTINEL-YAML" not in summary


def test_validate_sync_result_accepts_timezone_aware_published_at():
    result = validate_sync_result(
        SyncResult(candidates=[_candidate(published_at=datetime(2026, 1, 1, tzinfo=UTC))])
    )

    assert result.candidates[0].published_at is not None


def test_describe_error_drops_untrusted_message_text():
    message = describe_error(
        RuntimeError("failed https://user:secret@example.invalid/feed?token=abcd1234")
    )

    assert message == "RuntimeError"
