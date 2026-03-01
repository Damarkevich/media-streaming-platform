from datetime import datetime

from pydantic import BaseModel

from src.models.log import LogType


class LogResponse(BaseModel):
    """Response schema for user audit log entry."""

    log_type: LogType
    created_at: datetime
