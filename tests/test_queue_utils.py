import asyncio

import pytest

from src.queue_utils import BoundedQueue, DeadLetterQueue


class TestBoundedQueue:
    def test_bounded_queue_eviction(self):
        q = BoundedQueue(3)
        q.put_nowait("a")
        q.put_nowait("b")
        q.put_nowait("c")
        q.put_nowait("d")

        assert q.get_nowait() == "b"
        assert q.get_nowait() == "c"
        assert q.get_nowait() == "d"
        assert q.empty()

    @pytest.mark.asyncio
    async def test_bounded_queue_async_put(self):
        q = BoundedQueue(3)
        q.put_nowait("a")
        q.put_nowait("b")
        q.put_nowait("c")
        # 4th put via async — should not raise QueueFull
        await q.put("d")

        assert q.get_nowait() == "b"
        assert q.get_nowait() == "c"
        assert q.get_nowait() == "d"

    def test_bounded_queue_single_item(self):
        q = BoundedQueue(1)
        q.put_nowait("first")
        q.put_nowait("second")

        assert q.get_nowait() == "second"
        assert q.empty()

    def test_bounded_queue_normal_operation(self):
        q = BoundedQueue(3)
        q.put_nowait("x")
        assert q.get_nowait() == "x"
        assert q.empty()


class TestDeadLetterQueue:
    @pytest.mark.asyncio
    async def test_dlq_snapshot(self):
        dlq = DeadLetterQueue()
        await dlq.put("a")
        await dlq.put("b")
        await dlq.put("c")

        snap = dlq.snapshot()
        assert snap["depth"] == 3
        assert snap["total_accumulated"] == 3

    @pytest.mark.asyncio
    async def test_dlq_get(self):
        dlq = DeadLetterQueue()
        await dlq.put("a")
        await dlq.put("b")
        await dlq.put("c")

        got = await dlq.get()
        assert got == "a"

        snap = dlq.snapshot()
        assert snap["depth"] == 2
        assert snap["total_accumulated"] == 2

    @pytest.mark.asyncio
    async def test_dlq_retry_all(self):
        dlq = DeadLetterQueue()
        await dlq.put("x")
        await dlq.put("y")
        await dlq.put("z")

        target = asyncio.Queue()
        count = await dlq.retry_all(target)

        assert count == 3
        assert target.qsize() == 3
        assert target.get_nowait() == "x"
        assert target.get_nowait() == "y"
        assert target.get_nowait() == "z"
        assert dlq._queue.empty()

    @pytest.mark.asyncio
    async def test_dlq_retry_empty(self):
        dlq = DeadLetterQueue()
        target = asyncio.Queue()
        count = await dlq.retry_all(target)

        assert count == 0
        assert target.empty()
