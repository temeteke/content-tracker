import json
from datetime import datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from pydantic import ValidationError as PydanticValidationError

from content_tracker_plugin_api import ContentCandidate, SyncResult

from .models import ContentType

MAX_TITLE_LENGTH = 500
MAX_URL_LENGTH = 2000
MAX_DURATION_SECONDS = 2_147_483_647
MAX_ERROR_LENGTH = 300

_url_validator = URLValidator(schemes=["http", "https"])


class PluginOutputError(ValueError):
    pass


def normalize_http_url(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("url must be a string")
    url = value.strip()
    if not url:
        raise ValueError("url must not be empty")
    if len(url) > MAX_URL_LENGTH:
        raise ValueError(f"url must be at most {MAX_URL_LENGTH} characters")
    try:
        _url_validator(url)
    except ValidationError as exc:
        raise ValueError("url must be a valid HTTP(S) URL") from exc
    return url


def _is_json_compatible(value: Any) -> bool:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _validate_datetime(value: Any, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, datetime):
        raise PluginOutputError(f"{label} must be a datetime or null")
    if value.tzinfo is None or value.utcoffset() is None:
        raise PluginOutputError(f"{label} must include a timezone")


def _validate_mapping(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise PluginOutputError(f"{label} must be a mapping")
    if not _is_json_compatible(value):
        raise PluginOutputError(f"{label} must be JSON serializable")


def validate_candidate(index: int, candidate: Any) -> ContentCandidate:
    if not isinstance(candidate, ContentCandidate):
        raise PluginOutputError(f"candidate {index} must be a ContentCandidate")

    if not isinstance(candidate.title, str):
        raise PluginOutputError(f"candidate {index} title must be a string")
    title = candidate.title.strip()
    if not title:
        raise PluginOutputError(f"candidate {index} title must not be empty")
    if len(title) > MAX_TITLE_LENGTH:
        raise PluginOutputError(
            f"candidate {index} title must be at most {MAX_TITLE_LENGTH} characters"
        )

    if candidate.content_type not in ContentType.values:
        raise PluginOutputError(f"candidate {index} has an unsupported content type")

    try:
        url = normalize_http_url(candidate.url)
    except ValueError as exc:
        raise PluginOutputError(f"candidate {index} url is invalid: {exc}") from exc

    duration = candidate.duration_seconds
    if duration is not None and (
        not isinstance(duration, int)
        or isinstance(duration, bool)
        or duration < 0
        or duration > MAX_DURATION_SECONDS
    ):
        raise PluginOutputError(
            f"candidate {index} duration_seconds must be between 0 and "
            f"{MAX_DURATION_SECONDS} or null"
        )

    _validate_datetime(candidate.published_at, f"candidate {index} published_at")
    _validate_mapping(candidate.metadata, f"candidate {index} metadata")

    return ContentCandidate(
        title=title,
        content_type=candidate.content_type,
        url=url,
        published_at=candidate.published_at,
        duration_seconds=duration,
        metadata=dict(candidate.metadata),
    )


def validate_sync_result(result: Any) -> SyncResult:
    if not isinstance(result, SyncResult):
        raise PluginOutputError("adapter fetch must return a SyncResult")
    if not isinstance(result.candidates, list):
        raise PluginOutputError("SyncResult.candidates must be a list")

    candidates = [
        validate_candidate(index, candidate) for index, candidate in enumerate(result.candidates)
    ]

    if not isinstance(result.next_state, dict):
        raise PluginOutputError("SyncResult.next_state must be a mapping")
    if not _is_json_compatible(result.next_state):
        raise PluginOutputError("SyncResult.next_state must be JSON serializable")

    return SyncResult(candidates=candidates, next_state=dict(result.next_state))


def _format_pydantic_error(exc: PydanticValidationError, *, include_message: bool) -> str:
    details = []
    for error in exc.errors(include_input=False, include_url=False):
        location = ".".join(str(part) for part in error.get("loc", ()))
        if include_message:
            text = error.get("msg", "")
        else:
            text = error.get("type", "")
        if not text:
            continue
        details.append(f"{location}: {text}" if location else text)
    return "; ".join(detail for detail in details if detail)


def describe_error(exc: BaseException) -> str:
    """Summarize an error from untrusted (adapter) code.

    Only structurally value-free content is included: the exception class
    name, and for Pydantic errors the field path plus error code. Free-text
    messages and input values are never emitted.
    """
    if isinstance(exc, PydanticValidationError):
        summary = _format_pydantic_error(exc, include_message=False)
        text = f"ValidationError: {summary}" if summary else "ValidationError"
    else:
        text = type(exc).__name__
    return text[:MAX_ERROR_LENGTH]


def describe_host_error(exc: BaseException) -> str:
    """Summarize an error from host code.

    Host messages are authored in this repository and audited to be
    value-free, so the message text is preserved for diagnostics.
    """
    if isinstance(exc, PydanticValidationError):
        summary = _format_pydantic_error(exc, include_message=True)
        text = f"ValidationError: {summary}" if summary else "ValidationError"
    else:
        message = str(exc)
        text = f"{type(exc).__name__}: {message}" if message else type(exc).__name__
    return text[:MAX_ERROR_LENGTH]
