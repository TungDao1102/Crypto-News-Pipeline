import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

ALERT_COOLDOWN_SECONDS = 1800

HealthCheckFn = Callable[[], Awaitable[dict[str, Any]]]

_STARTUP_EVENT_TYPES = [
    "source_disconnect",
    "all_models_exhausted",
    "queue_overflow",
    "binance_daily_limit",
    "publisher_permanent_error",
]


@dataclass
class CheckEntry:
    check_fn: HealthCheckFn
    timeout: float = 5.0


class HealthCollector:
    def __init__(self, alert_cooldown: float = ALERT_COOLDOWN_SECONDS):
        self._checks: dict[str, CheckEntry] = {}
        self._alert_cooldowns: dict[str, float] = {}
        self._alert_cooldown_duration = alert_cooldown
        self._bot = None
        self._admin_chat_id: str | None = None

        now = time.monotonic()
        for event_type in _STARTUP_EVENT_TYPES:
            self._alert_cooldowns[event_type] = now

    def set_bot(self, bot, admin_chat_id: str) -> None:
        self._bot = bot
        self._admin_chat_id = admin_chat_id

    def register(self, name: str, check_fn: HealthCheckFn, timeout: float = 5.0) -> None:
        if name in self._checks:
            logger.warning("Health check '%s' already registered, overwriting", name)
        self._checks[name] = CheckEntry(check_fn=check_fn, timeout=timeout)

    def can_send_alert(self, event_type: str) -> bool:
        now = time.monotonic()
        last_alert = self._alert_cooldowns.get(event_type)
        if last_alert is None or (now - last_alert) >= self._alert_cooldown_duration:
            self._alert_cooldowns[event_type] = now
            return True
        return False

    def send_alert(self, event_type: str, message: str) -> None:
        if self._bot is None:
            logger.warning("Bot not set, cannot send alert for '%s'", event_type)
            return
        if not self.can_send_alert(event_type):
            logger.debug("Alert '%s' suppressed by cooldown", event_type)
            return
        try:
            self._bot.send_message(chat_id=self._admin_chat_id, text=f"\u26a0\ufe0f {message}")
        except Exception:
            logger.exception("Failed to send alert for '%s'", event_type)

    async def get_report(self) -> dict[str, Any]:
        async def run_check(name: str, entry: CheckEntry) -> tuple[str, dict[str, Any]]:
            try:
                result = await asyncio.wait_for(entry.check_fn(), timeout=entry.timeout)
                return name, {"status": "ok", "data": result}
            except TimeoutError:
                return name, {"status": "timeout", "error": f"Check timed out after {entry.timeout}s"}
            except Exception as e:
                return name, {"status": "error", "error": str(e)}

        tasks = [run_check(name, entry) for name, entry in self._checks.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        checks: dict[str, Any] = {}
        overall = "healthy"
        for r in results:
            if isinstance(r, BaseException):
                logger.error("Unexpected exception in gather: %s", r)
                continue
            name, check_result = r
            checks[name] = check_result
            if check_result["status"] != "ok":
                overall = "degraded"

        return {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": overall,
            "checks": checks,
        }
