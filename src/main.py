import asyncio
import logging
import signal
import sys

import httpx

from src.ai_handler import AIConsumer, TokenBucket
from src.bot_reviewer import run_bot
from src.config import ConfigError, load_config
from src.crawler import TelegramCrawler
from src.health import HealthCollector
from src.logging_setup import setup_logging
from src.metrics import DailyMetrics
from src.models import DraftContent, RawMessage
from src.queue_utils import BoundedQueue, DeadLetterQueue
from src.system_state import SystemState

logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        config = load_config()
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    setup_logging()
    if config.log_levels:
        from src.logging_setup import configure_module_levels
        configure_module_levels(config.log_levels)
    logger.info("Configuration loaded successfully")

    raw_queue: BoundedQueue[RawMessage] = BoundedQueue(200)
    result_queue: BoundedQueue[DraftContent] = BoundedQueue(200)
    publish_queue: BoundedQueue[DraftContent] = BoundedQueue(200)

    system_state = SystemState()
    health_collector = HealthCollector()
    dlq = DeadLetterQueue()
    daily_metrics = DailyMetrics()

    channel_tags = {
        s.channel: s.tags
        for s in config.sources
        if s.enabled
    }
    token_bucket = TokenBucket(capacity=10, refill_rate=2.0)

    crawler = TelegramCrawler(config, raw_queue)
    crawler.register_health(health_collector)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0, read=30.0),
        limits=httpx.Limits(max_connections=10),
    ) as http_client:
        ai_consumer = AIConsumer(
            raw_queue=raw_queue,
            result_queue=result_queue,
            channel_tags=channel_tags,
            rate_limiter=token_bucket,
            http_client=http_client,
            api_key=config.openrouter_api_key,
        )
        ai_consumer.register_health(health_collector)

        bot_task = asyncio.create_task(
            run_bot(
                token=config.bot_token,
                system_state=system_state,
                admin_chat_id=config.admin_chat_id,
                result_queue=result_queue,
                publish_queue=publish_queue,
                http_client=http_client,
                binance_api_key=config.binance_square_api_key,
                telegram_channel_id=config.telegram_channel_id,
                health_collector=health_collector,
                dlq=dlq,
                daily_metrics=daily_metrics,
                raw_queue=raw_queue,
            )
        )

        async def log_queue_depths() -> None:
            while True:
                await asyncio.sleep(300)
                logger.info(
                    "Queue depths — raw: %d, result: %d, publish: %d",
                    raw_queue.qsize(),
                    result_queue.qsize(),
                    publish_queue.qsize(),
                )

        async def flush_metrics_periodically() -> None:
            while True:
                await asyncio.sleep(300)
                daily_metrics.flush()

        asyncio.create_task(log_queue_depths())
        asyncio.create_task(flush_metrics_periodically())

        loop = asyncio.get_running_loop()

        async def shutdown() -> None:
            logger.info("Shutting down...")
            daily_metrics.flush()
            await crawler.shutdown()
            await ai_consumer.shutdown()
            bot_task.cancel()
            dlq_snapshot = dlq.snapshot()
            if dlq_snapshot["total_accumulated"] > 0:
                logger.warning("DLQ has %d unprocessed items at shutdown", dlq_snapshot["total_accumulated"])
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()

        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda: asyncio.create_task(shutdown()),
                )
        except NotImplementedError:
            logger.info("Signal handler not supported on this platform")

        try:
            await asyncio.gather(
                crawler.start(),
                ai_consumer.start(),
                bot_task,
            )
        except asyncio.CancelledError:
            pass
        finally:
            await shutdown()


if __name__ == "__main__":
    asyncio.run(main())
