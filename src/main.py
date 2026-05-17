import asyncio
import logging
import signal
import sys

from src.config import ConfigError, load_config
from src.crawler import TelegramCrawler
from src.logging_setup import setup_logging
from src.models import RawMessage

logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        config = load_config()
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    setup_logging()
    logger.info("Configuration loaded successfully")

    queue: asyncio.Queue[RawMessage] = asyncio.Queue()
    crawler = TelegramCrawler(config, queue)

    loop = asyncio.get_running_loop()

    async def shutdown() -> None:
        logger.info("Shutting down...")
        await crawler.shutdown()
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(shutdown()),
        )

    try:
        await crawler.start()
    except asyncio.CancelledError:
        pass
    finally:
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())
