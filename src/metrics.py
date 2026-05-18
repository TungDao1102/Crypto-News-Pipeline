import asyncio
import json
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

METRICS_DIR = Path("logs/metrics")
FLUSH_INTERVAL = 300


class DailyMetrics:
    def __init__(self, metrics_dir: Path = METRICS_DIR) -> None:
        self.metrics_dir = metrics_dir
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self._counters: dict[str, int] = defaultdict(int)
        self._latencies: list[float] = []

    def increment(self, key: str) -> None:
        self._counters[key] += 1

    def record_latency(self, seconds: float) -> None:
        self._latencies.append(seconds)

    def _calculate_p95(self) -> float | None:
        if not self._latencies:
            return None
        sorted_lats = sorted(self._latencies)
        index = int(len(sorted_lats) * 0.95)
        return sorted_lats[index]

    def approve_reject_ratio(self) -> float | None:
        approved = self._counters.get("drafts_approved", 0)
        rejected = self._counters.get("drafts_rejected", 0)
        total = approved + rejected
        if total == 0:
            return None
        return approved / total

    def flush(self) -> None:
        metrics: dict[str, Any] = {
            "date": date.today().isoformat(),
            "counters": dict(self._counters),
        }

        if self._latencies:
            p95 = self._calculate_p95()
            if p95 is not None:
                metrics["api_latency_p95"] = p95

        filepath = self.metrics_dir / f"{date.today().isoformat()}.json"

        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                existing = json.load(f)

            existing_counters = existing.get("counters", {})
            for key, val in metrics["counters"].items():
                existing_counters[key] = existing_counters.get(key, 0) + val
            metrics["counters"] = existing_counters

            if "api_latency_p95" in metrics:
                existing_latencies = existing.get("latencies", [])
                metrics["latencies"] = existing_latencies + self._latencies

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        logger.info("Daily metrics flushed to %s", filepath)

    async def periodic_flush(self, interval: int = FLUSH_INTERVAL) -> None:
        while True:
            await asyncio.sleep(interval)
            self.flush()
