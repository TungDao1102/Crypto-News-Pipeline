from datetime import datetime
from pydantic import BaseModel


class SourceConfig(BaseModel):
    channel: str
    tags: list[str] = []
    enabled: bool = True


class RawMessage(BaseModel):
    source_channel: str
    message_id: int
    raw_text: str
    media_info: str | None = None
    timestamp: datetime
    content_hash: str


class ConfigError(Exception):
    pass
