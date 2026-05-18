import asyncio
import time

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
