import asyncio
import logging

logger = logging.getLogger(__name__)

DEFAULT_MAXSIZE = 200


class BoundedQueue(asyncio.Queue):
    def __init__(self, maxsize: int = 200):
        super().__init__(maxsize=maxsize)

    def put_nowait(self, item):
        if self.full():
            try:
                self.get_nowait()
                logger.info(
                    "Queue at capacity (%d) — dropped oldest item",
                    self.qsize(),
                )
            except asyncio.QueueEmpty:
                pass
        super().put_nowait(item)

    async def put(self, item):
        self.put_nowait(item)


class DeadLetterQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._count: int = 0

    async def put(self, item):
        await self._queue.put(item)
        self._count += 1
        logger.warning(
            "[ERR_DLQ] Item added to DLQ — total: %d",
            self._count,
        )

    async def get(self):
        item = await self._queue.get()
        self._count -= 1
        return item

    def snapshot(self) -> dict:
        return {"depth": self._queue.qsize(), "total_accumulated": self._count}

    async def retry_all(self, target_queue: asyncio.Queue) -> int:
        retried = 0
        while not self._queue.empty():
            item = self._queue.get_nowait()
            await target_queue.put(item)
            self._queue.task_done()
            retried += 1
        self._count = self._queue.qsize()
        return retried
