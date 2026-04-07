import json
import logging
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator

from config.settings import settings

logger = logging.getLogger(settings.log_name)


def _parse_timestamp(value: Any) -> datetime:
    """Parse supported timestamp representations into datetime."""
    if isinstance(value, datetime):
        return value

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)

    if isinstance(value, str):
        try:
            return datetime.fromtimestamp(float(value))
        except ValueError:
            return datetime.fromisoformat(value)

    raise ValueError("Unsupported timestamp format")


class RawEvent(BaseModel):
    """Validated raw event schema consumed from Kafka."""

    event_id: UUID
    user_id: UUID
    session_id: UUID
    event_type: str = "unknown"
    event_timestamp: datetime
    server_timestamp: datetime
    context: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_timestamp", "server_timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, value: Any) -> datetime:
        return _parse_timestamp(value)

    @field_validator("context", "payload", mode="before")
    @classmethod
    def ensure_dict(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return cast(dict[str, Any], value)
        raise ValueError("Must be an object")


class Transformer:
    """Validate and convert raw events into ClickHouse-ready rows."""

    def transform(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform a batch of raw events, skipping invalid records."""
        transformed: list[dict[str, Any]] = []
        processed_count = len(events)
        invalid_count = 0

        for event in events:
            try:
                raw_event = RawEvent.model_validate(event)
            except ValidationError:
                invalid_count += 1
                continue

            movie_id: UUID | None = None
            raw_movie_id = raw_event.payload.get("movie_id")
            if raw_movie_id is not None:
                try:
                    movie_id = UUID(str(raw_movie_id))
                except ValueError:
                    logger.debug("Invalid optional movie_id value: %s", raw_movie_id)

            transformed.append(
                {
                    "event_id": raw_event.event_id,
                    "user_id": raw_event.user_id,
                    "session_id": raw_event.session_id,
                    "event_type": raw_event.event_type,
                    "event_timestamp": raw_event.event_timestamp,
                    "server_timestamp": raw_event.server_timestamp,
                    "context": json.dumps(raw_event.context, default=str),
                    "payload": json.dumps(raw_event.payload, default=str),
                    "movie_id": movie_id,
                }
            )

        valid_count = len(transformed)
        if processed_count > 0:
            logger.info(
                "Transformer batch summary: processed=%s valid=%s invalid=%s",
                processed_count,
                valid_count,
                invalid_count,
            )

        return transformed
