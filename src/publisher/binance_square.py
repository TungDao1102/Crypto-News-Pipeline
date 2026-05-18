import logging
import re

import httpx

from src.logging_setup import ErrorCode, ec
from src.publisher.base import BasePublisher, PublisherResult

logger = logging.getLogger(__name__)

BINANCE_SQUARE_URL = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"

BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
ITALIC_PATTERN = re.compile(r"\*(.+?)\*")
LINK_PATTERN = re.compile(r"\[(.+?)\]\(.+?\)")
HEADING_PATTERN = re.compile(r"^#+\s*", re.MULTILINE)


def strip_markdown(text: str) -> str:
    text = BOLD_PATTERN.sub(r"\1", text)
    text = ITALIC_PATTERN.sub(r"\1", text)
    text = LINK_PATTERN.sub(r"\1", text)
    text = HEADING_PATTERN.sub("", text)
    return text.strip()


class BinanceSquareClient:

    def __init__(
        self,
        api_key: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._api_key = api_key
        self._http_client = http_client

    async def post_content(self, text: str) -> dict:
        headers = {
            "X-Square-OpenAPI-Key": self._api_key,
            "Content-Type": "application/json",
            "clienttype": "binanceSkill",
        }
        body = {"bodyTextOnly": text}
        response = await self._http_client.post(
            BINANCE_SQUARE_URL,
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        return response.json()


class BinanceSquarePublisher(BasePublisher):

    def __init__(self, client: BinanceSquareClient, telegram_channel: str | None = None) -> None:
        self._client = client
        self._telegram_channel = telegram_channel

    async def publish(self, content: str) -> PublisherResult:
        cleaned = strip_markdown(content)
        if not cleaned:
            logger.warning(ec(ErrorCode.BINANCE_DAILY_LIMIT, "Binance Square: empty content after Markdown stripping"))
            return PublisherResult(
                platform="binance_square",
                success=False,
                error="Empty content after Markdown stripping",
            )
        try:
            data = await self._client.post_content(cleaned)
            code = data.get("code", "")
            if code == "000000":
                post_id = data.get("data", {}).get("id")
                if not post_id:
                    logger.warning(
                        "Binance Square: success code but no post ID — post may have succeeded"
                    )
                    return PublisherResult(
                        platform="binance_square",
                        success=True,
                        url=None,
                        error="Success but no post ID returned",
                    )
                url = f"https://www.binance.com/en/square/post/{post_id}"
                logger.info("Published to Binance Square: %s", url)
                return PublisherResult(
                    platform="binance_square",
                    success=True,
                    url=url,
                    error=None,
                    post_id=str(post_id),
                )
            if code == "220009":
                logger.warning(ec(ErrorCode.BINANCE_DAILY_LIMIT, "Binance Square: daily limit reached (code 220009)"))
                return PublisherResult(
                    platform="binance_square",
                    success=False,
                    error="Daily limit reached (220009)",
                )
            error_msg = data.get("message", f"Error code {code}")
            logger.error(ec(ErrorCode.PUBLISH_FAIL, "Binance Square publish failed: %s"), error_msg)
            return PublisherResult(
                platform="binance_square",
                success=False,
                error=error_msg,
            )
        except httpx.TimeoutException:
            logger.error(ec(ErrorCode.PUBLISH_FAIL, "Binance Square: timeout"))
            return PublisherResult(
                platform="binance_square",
                success=False,
                error="Timeout",
            )
        except httpx.HTTPStatusError as e:
            logger.error(ec(ErrorCode.PUBLISH_FAIL, "Binance Square: HTTP %s"), e.response.status_code)
            return PublisherResult(
                platform="binance_square",
                success=False,
                error=f"HTTP {e.response.status_code}",
            )

    async def close(self) -> None:
        pass
