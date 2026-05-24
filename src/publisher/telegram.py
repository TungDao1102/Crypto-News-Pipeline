import logging

from telegram import Bot
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut

from src.logging_setup import ErrorCode, ec
from src.publisher.base import BasePublisher, PublisherResult

logger = logging.getLogger(__name__)

HTML_ESCAPE_TABLE = str.maketrans({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
})


class TelegramPublisher(BasePublisher):

    def __init__(self, bot: Bot, chat_id: str | int) -> None:
        self._bot = bot
        self._chat_id = chat_id

    async def publish(self, content: str) -> PublisherResult:
        safe_content = content.translate(HTML_ESCAPE_TABLE)
        try:
            message = await self._bot.send_message(
                chat_id=self._chat_id,
                text=safe_content,
                parse_mode="HTML",
            )
            url = f"https://t.me/{self._chat_id}/{message.message_id}"
            logger.info("Published to Telegram: %s", url)
            return PublisherResult(
                platform="telegram",
                success=True,
                url=url,
                error=None,
            )
        except Forbidden:
            logger.error(ec(ErrorCode.BOT_PERMISSION, "Telegram publish: bot was kicked or blocked from channel"))
            return PublisherResult(
                platform="telegram",
                success=False,
                error="Bot kicked or blocked from channel",
            )
        except RetryAfter as e:
            logger.warning(ec(ErrorCode.PUBLISH_FAIL, "Telegram publish: rate limited, retry after %ds"), e.retry_after)
            return PublisherResult(
                platform="telegram",
                success=False,
                error=f"Rate limited: retry after {e.retry_after}s",
            )
        except (BadRequest, NetworkError, TimedOut) as e:
            logger.error(ec(ErrorCode.PUBLISH_FAIL, "Telegram publish failed: %s"), e)
            return PublisherResult(
                platform="telegram",
                success=False,
                error=str(e),
            )

    async def close(self) -> None:
        pass
