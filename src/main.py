import asyncio
import logging
import signal
import sys

import httpx

from src.ai_handler import AIConsumer, TokenBucket
from src.bot_reviewer import run_bot
from src.config import ConfigError, load_config
from src.crawler import TelegramCrawler
from src.logging_setup import setup_logging
from src.models import DraftContent, RawMessage
from src.system_state import SystemState

logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        config = load_config()
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    setup_logging()
    logger.info("Configuration loaded successfully")

    raw_queue: asyncio.Queue[RawMessage] = asyncio.Queue()
    result_queue: asyncio.Queue[DraftContent] = asyncio.Queue()
    publish_queue: asyncio.Queue[DraftContent] = asyncio.Queue()

    system_state = SystemState()

    channel_tags = {
        s.channel: s.tags
        for s in config.sources
        if s.enabled
    }
    token_bucket = TokenBucket(capacity=10, refill_rate=2.0)

    crawler = TelegramCrawler(config, raw_queue)

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

        bot_task = asyncio.create_task(
            run_bot(
                token=config.bot_token,
                system_state=system_state,
                admin_chat_id=config.admin_chat_id,
                result_queue=result_queue,
                publish_queue=publish_queue,
            )
        )

        loop = asyncio.get_running_loop()

        async def shutdown() -> None:
            logger.info("Shutting down...")
            await crawler.shutdown()
            await ai_consumer.shutdown()
            bot_task.cancel()
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
