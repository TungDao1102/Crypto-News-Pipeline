import asyncio
import logging

import httpx
from telegram import Bot

from src.logging_setup import ErrorCode, ec
from src.models import DraftContent, PublishResult
from src.publisher.binance_square import BinanceSquareClient, BinanceSquarePublisher
from src.publisher.tag_injector import TagInjector
from src.publisher.telegram import TelegramPublisher
from src.queue_utils import DeadLetterQueue
from src.system_state import SystemState

logger = logging.getLogger(__name__)

PUBLISH_COOLDOWN_SECONDS = 2


class PublisherConsumer:

    def __init__(
        self,
        publish_queue: asyncio.Queue[DraftContent],
        system_state: SystemState,
        http_client: httpx.AsyncClient,
        binance_api_key: str,
        bot: Bot,
        telegram_channel_id: str,
        dlq: DeadLetterQueue | None = None,
        health_collector = None,
    ) -> None:
        self._publish_queue = publish_queue
        self._system_state = system_state
        self._shutdown = asyncio.Event()
        self._dlq = dlq
        self._health_collector = health_collector

        self._tag_injector = TagInjector()
        self._telegram_publisher = TelegramPublisher(bot, telegram_channel_id)
        binance_client = BinanceSquareClient(binance_api_key, http_client)
        self._binance_publisher = BinanceSquarePublisher(binance_client)
        self._published_ids: set[str] = set()
        self._last_publish_time: str | None = None
        self._last_publish_success: bool | None = None

    async def start(self) -> None:
        logger.info("Publisher consumer started")
        worker = asyncio.create_task(self._worker())
        try:
            await worker
        except asyncio.CancelledError:
            logger.info("Publisher consumer cancelled")

    def register_health(self, health_collector) -> None:
        from src.health import HealthCollector
        self._health_collector = health_collector
        health_collector.register("publisher", self._check_health, timeout=5.0)

    async def _check_health(self) -> dict:
        return {
            "last_publish_at": self._last_publish_time,
            "last_publish_success": self._last_publish_success,
            "processed_total": len(self._published_ids),
        }

    async def shutdown(self) -> None:
        self._shutdown.set()
        await self._telegram_publisher.close()
        await self._binance_publisher.close()
        logger.info("Publisher consumer shut down")

    async def _worker(self) -> None:
        while not self._shutdown.is_set():
            qsize = self._publish_queue.qsize()
            if qsize > 10:
                logger.warning(
                    ec(ErrorCode.PUBLISH_FAIL, "Publish queue backpressure: size=%d"), qsize,
                )

            draft = await self._publish_queue.get()
            try:
                if draft.title_vn in self._published_ids:
                    logger.info("Skipping already-published draft: %s", draft.title_vn)
                    continue

                await self._publish_to_platforms(draft)
                self._published_ids.add(draft.title_vn)
            except Exception:
                logger.exception(ec(ErrorCode.PUBLISH_FAIL, "Publisher: unexpected error processing draft %s", draft.title_vn))
                if self._dlq:
                    await self._dlq.put(draft)
                    logger.warning("Draft '%s' moved to DLQ", draft.title_vn)
            finally:
                self._publish_queue.task_done()

    async def _publish_to_platforms(self, draft: DraftContent) -> None:
        results: list[PublishResult] = []

        telegram_content = self._tag_injector.inject(
            content=draft.telegram_markdown,
            content_tags=draft.tags,
            max_length=4096,
        )
        result = await self._telegram_publisher.publish(telegram_content)
        results.append(result)
        logger.info("Telegram result for '%s': success=%s, url=%s", draft.title_vn, result.success, result.url)

        await asyncio.sleep(PUBLISH_COOLDOWN_SECONDS)

        binance_content = self._tag_injector.inject(
            content=draft.binance_square_markdown,
            content_tags=draft.tags,
            max_length=4000,
        )
        result = await self._binance_publisher.publish(binance_content)
        results.append(result)
        logger.info("Binance Square result for '%s': success=%s, url=%s", draft.title_vn, result.success, result.url)

        any_success = any(r.success for r in results)
        from datetime import datetime
        self._last_publish_time = datetime.utcnow().isoformat() + "Z"
        self._last_publish_success = any_success
        if any_success:
            draft.status = "published"
            await self._system_state.increment_processed()
            logger.info("Draft published: %s", draft.title_vn)
        else:
            logger.warning(ec(ErrorCode.PUBLISH_FAIL, "Draft failed on all platforms: %s"), draft.title_vn)

        for result in results:
            if result.platform == "binance_square" and not result.success:
                if result.error and "220009" in result.error:
                    if self._health_collector:
                        await self._health_collector.send_alert(
                            "binance_daily_limit",
                            "Binance Square daily limit (220009) reached \u2014 publishes paused until reset",
                        )
                elif result.error and "Daily limit" not in (result.error or ""):
                    if self._health_collector:
                        await self._health_collector.send_alert(
                            "publisher_permanent_error",
                            f"Binance Square publish failed: {result.error}",
                        )
            if result.platform == "telegram" and not result.success:
                if result.error and ("kicked" in result.error.lower() or "blocked" in result.error.lower()):
                    if self._health_collector:
                        await self._health_collector.send_alert(
                            "publisher_permanent_error",
                            f"Telegram bot kicked or blocked from channel: {result.error}",
                        )
