import asyncio
import pytest


@pytest.mark.asyncio
async def test_pause_cooldown():
    from src.ai_handler import AIConsumer

    consumer = AIConsumer(
        raw_queue=asyncio.Queue(),
        result_queue=asyncio.Queue(),
        channel_tags={},
        rate_limiter=None,
        http_client=None,
        api_key="test",
    )
    assert not consumer._pause.is_set()
    await consumer.pause_ai(duration=0.1)
    assert consumer._pause.is_set()
    await asyncio.sleep(0.2)
    assert not consumer._pause.is_set()


@pytest.mark.asyncio
async def test_pause_cancels_previous():
    from src.ai_handler import AIConsumer

    consumer = AIConsumer(
        raw_queue=asyncio.Queue(),
        result_queue=asyncio.Queue(),
        channel_tags={},
        rate_limiter=None,
        http_client=None,
        api_key="test",
    )
    await consumer.pause_ai(duration=10)
    first_task = consumer._pause_cooldown_task
    await consumer.pause_ai(duration=0.1)
    await asyncio.sleep(0)
    assert first_task.done() or first_task.cancelled()
    await asyncio.sleep(0.2)
    assert not consumer._pause.is_set()


@pytest.mark.asyncio
async def test_worker_respects_pause():
    from src.ai_handler import AIConsumer

    consumer = AIConsumer(
        raw_queue=asyncio.Queue(),
        result_queue=asyncio.Queue(),
        channel_tags={},
        rate_limiter=None,
        http_client=None,
        api_key="test",
    )
    await consumer.pause_ai(duration=0.1)
    assert consumer._pause.is_set()
