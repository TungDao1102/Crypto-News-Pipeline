import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from src.health import HealthCollector


@pytest.mark.asyncio
async def test_register_and_report():
    collector = HealthCollector()

    async def check_ok() -> dict:
        return {"status": "ok"}

    async def check_db() -> dict:
        return {"connections": 5}

    collector.register("api", check_ok)
    collector.register("db", check_db)

    report = await collector.get_report()
    assert report["status"] == "healthy"
    assert "api" in report["checks"]
    assert "db" in report["checks"]
    assert report["checks"]["api"]["status"] == "ok"
    assert report["checks"]["db"]["status"] == "ok"


@pytest.mark.asyncio
async def test_check_timeout():
    collector = HealthCollector()

    async def slow_check() -> dict:
        await asyncio.sleep(10)
        return {"ok": True}

    collector.register("slow", slow_check, timeout=0.01)

    report = await collector.get_report()
    assert report["checks"]["slow"]["status"] == "timeout"


@pytest.mark.asyncio
async def test_check_error():
    collector = HealthCollector()

    async def failing_check() -> dict:
        raise RuntimeError("database unreachable")

    collector.register("db", failing_check)

    report = await collector.get_report()
    assert report["checks"]["db"]["status"] == "error"
    assert "database unreachable" in report["checks"]["db"]["error"]


def test_alert_cooldown_suppresses_duplicates():
    collector = HealthCollector(alert_cooldown=10)

    assert collector.can_send_alert("test_event") is True
    assert collector.can_send_alert("test_event") is False


def test_alert_cooldown_allows_after_window():
    collector = HealthCollector(alert_cooldown=10)

    assert collector.can_send_alert("test_event") is True

    past = time.monotonic() - 20
    collector._alert_cooldowns["test_event"] = past

    assert collector.can_send_alert("test_event") is True


def test_startup_alert_storm_prevention():
    expected = {
        "source_disconnect",
        "all_models_exhausted",
        "queue_overflow",
        "binance_daily_limit",
        "publisher_permanent_error",
    }
    collector = HealthCollector()
    assert expected.issubset(collector._alert_cooldowns.keys())


@pytest.mark.asyncio
async def test_send_alert_with_bot_sends_message():
    collector = HealthCollector()
    bot = AsyncMock()
    collector.set_bot(bot, admin_chat_id="@admin")
    await collector.send_alert("test_event", "Something happened")
    bot.send_message.assert_called_once()
    assert bot.send_message.call_args.kwargs["chat_id"] == "@admin"
    assert "⚠️" in bot.send_message.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_send_alert_without_bot_does_not_crash():
    collector = HealthCollector()
    await collector.send_alert("test_event", "Something happened")


@pytest.mark.asyncio
async def test_send_alert_respects_cooldown():
    collector = HealthCollector(alert_cooldown=10)
    bot = AsyncMock()
    collector.set_bot(bot, admin_chat_id="@admin")
    await collector.send_alert("cooldown_test", "First alert")
    assert bot.send_message.call_count == 1
    await collector.send_alert("cooldown_test", "Second alert")
    assert bot.send_message.call_count == 1


@pytest.mark.asyncio
async def test_get_report_overall_degraded():
    collector = HealthCollector()

    async def ok_check() -> dict:
        return {"status": "ok"}

    async def fail_check() -> dict:
        raise RuntimeError("broken")

    collector.register("ok", ok_check)
    collector.register("fail", fail_check)

    report = await collector.get_report()
    assert report["status"] == "degraded"
