from datetime import datetime
from typing import Literal

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


class DraftContent(BaseModel):
    title_vn: str
    telegram_markdown: str
    binance_square_markdown: str
    status: Literal["pending", "approved", "rejected", "published"] = "pending"
    tags: list[str] = []
    used_fallback: bool = False


class PublishResult(BaseModel):
    platform: Literal["telegram", "binance_square"]
    success: bool
    url: str | None = None
    error: str | None = None
    post_id: str | None = None


class ConfigError(Exception):
    pass
