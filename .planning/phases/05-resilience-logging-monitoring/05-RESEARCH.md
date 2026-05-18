# Phase 5: Resilience, Logging & Monitoring — Research

**Researched:** 2026-05-17
**Domain:** System hardening, failure detection, structured logging, metrics aggregation
**Confidence:** HIGH — all patterns are well-established Python stdlib patterns with no new third-party dependencies

---

## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 through D-18)

**Alert Delivery & Health Command**
- D-01: Alerts via existing PTB bot `send_message` to `ADMIN_CHAT_ID`; `/health` command for on-demand status
- D-02: Alert triggers: source disconnect after max retries, queue depth >50 critical, Binance daily limit (220009), publisher permanent errors
- D-03: Alert dedup: first-only per event type with 30-minute cooldown window
- D-04: `/health` shows per-module status + timestamps (crawler, AI, publisher, queue depths)
- D-05: Auto-pause AI only on `AllModelsExhausted`. 5-minute pause + auto-resume. Source disconnect does NOT pause AI
- D-06: `/health` as standalone `HealthCollector` module (`src/health.py`). Registry pattern

**Queue Auto-Mitigation & Overflow**
- D-07: Queue depth >50 → auto-switch to MANUAL + alert sent. Admin must manually switch back via `/mode_auto`
- D-08: Hard cap of 200 per queue. Drop oldest when exceeded
- D-09: Simple in-memory DLQ (`asyncio.Queue`) for persistently failing messages. Inspectable via `/health`
- D-10: Auto-pause: `asyncio.Event` + cooldown timer inside AIConsumer. Not conflated with rate limiter

**Logging Format & Levels**
- D-11: Keep human-readable log format. No JSON logging
- D-12: Config-driven per-module log levels via `LOG_LEVELS` config (JSON dict)
- D-13: Structured error codes: `[ERR_QUEUE_OVERFLOW]`, `[ERR_ALL_MODELS_EXHAUSTED]`, etc.
- D-14: Increased retention: 50MB × 10 backups (was 10MB × 5)

**Metrics Tracking**
- D-15: v1 metrics: approve/reject ratio (daily), JSON validation errors (daily), API latency P95 (hourly)
- D-16: Metrics via daily aggregate file (`logs/metrics/YYYY-MM-DD.json`) + extended `/status`
- D-17: Queue depth snapshots via existing `logger.info` — no dedicated file in v1
- D-18: Daily metrics are per-day aggregates (end-of-day rollup), not per-event append

### the agent's Discretion
- Exact error code strings and code list
- `/health` response format details
- Metrics file schema (exact JSON structure)
- Which events to log at which level for structured codes
- DLQ admin retry mechanism implementation
- Health check callback interface (how modules register)
- Queue hard cap constants (200 vs other value if testing shows different)
- Cooldown timer duration for alerts (30 min default, fine-tune later)
- Cooldown timer location (HealthCollector vs per-module)

### Deferred (OUT OF SCOPE)
- JSON logging for log aggregation pipeline
- Queue depth time-series metrics file
- Per-event metrics append
- Auto-retry with exponential backoff for failed platforms
- Alert routing via PagerDuty/email
- Persistent DLQ (database-backed)

---

## Summary

Phase 5 is a hardening-only phase that adds failure detection, alerting, health introspection, queue overflow handling, structured logging, and daily metrics across all 4 prior pipeline stages. It introduces zero new features and zero new third-party dependencies — everything is built on Python stdlib (`logging`, `asyncio`, `time`, `json`, `pathlib`) and the existing PTB bot for alert delivery.

**The 6 key implementation areas are:**
1. **HealthCollector** (`src/health.py`) — registry-based callback pattern, each module registers a check function
2. **Alert cooldown** — per-event-type `dict[str, float]` timestamp tracker in HealthCollector
3. **Queue cap + drop-oldest** — thin wrapper around `asyncio.Queue` that evicts oldest when full
4. **asyncio Event cooldown** — second `asyncio.Event` in `AIConsumer` with auto-reset timer
5. **Config-driven log levels** — `logging.getLogger(name).setLevel(level)` applied at startup
6. **Daily metrics** — in-memory counter object, flushed to `logs/metrics/YYYY-MM-DD.json` on shutdown

**Primary recommendation:** Use a `HealthCollector` class with a `register(name, check_fn, timeout)` interface. Module check functions are simple async coroutines returning a status dict. The collector runs all checks concurrently with `asyncio.gather()`, applies per-check timeouts, and formats the `/health` response.

---

## Standard Stack

### Core (All stdlib — no new third-party packages)
| Module | Purpose | Why Standard |
|--------|---------|--------------|
| `logging` | Per-module log level config, structured error code prefixes | Already used throughout; `getLogger(name).setLevel()` is the canonical Python pattern [VERIFIED: python docs] |
| `asyncio.Queue` | Queue cap wrapper base, DLQ backing | Already used for all 3 queues; `qsize()` enables depth monitoring |
| `asyncio.Event` | AI pause cooldown mechanism | Already used for shutdown pattern in `AIConsumer` [VERIFIED: src/ai_handler.py L372] |
| `time.monotonic()` | Alert cooldown timestamps | Cannot go backwards (unlike `time.time()`); correct for duration measurement [VERIFIED: python docs] |
| `json` | Daily metrics file serialization | Already used throughout; `json.dump(metrics_dict, f, indent=2)` for readable files |
| `pathlib.Path` | Metrics directory management | Already used in `logging_setup.py` for log directory [VERIFIED: src/logging_setup.py L21] |
| `dataclasses` or `TypedDict` | Error code registry, metrics accumulator | Lightweight, no Pydantic overhead for internal-only data |

### Reused Existing Modules
| Module | Purpose | How Reused |
|--------|---------|------------|
| `src/bot_reviewer.py` | Alert delivery | Reuse `send_message` to `ADMIN_CHAT_ID` (startup_notification pattern); register `/health` handler |
| `src/ai_handler.py` | Cooldown Event pattern | Add second `asyncio.Event` alongside `_shutdown`; workers check both before processing |
| `src/system_state.py` | Mode state + processed count | Add daily metrics counters; extend `/status` output |
| `src/logging_setup.py` | Log rotation config | Modify retention (50MB × 10); add per-module level application |

### Installation
```bash
# No new packages needed. This phase uses only Python stdlib + existing dependencies.
```

---

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PHASE 5 — HARDENING LAYER                          │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  src/health.py — HealthCollector                                   │     │
│  │                                                                     │     │
│  │  Registry:                                                         │     │
│  │    "crawler"  ──► crawler.check_health()  ──► (connected, last_msg) │     │
│  │    "ai"       ──► ai_consumer.check_health() ──► (workers, status) │     │
│  │    "publisher"──► publisher.check_health() ──► (last_publish, …)   │     │
│  │    "queues"   ──► queue_depth_check() ──► (raw, result, publish)    │     │
│  │                                                                     │     │
│  │  Async gather + per-check timeout → dict response                   │     │
│  └───────────────────────┬────────────────────────────────────────────┘     │
│                          │                                                  │
│                          ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  Alert Manager (inside HealthCollector)                           │     │
│  │                                                                     │     │
│  │  alert_cooldowns: dict[str, float]  ← {event_type: timestamp}     │     │
│  │  send_alert(event_type, message) → PTB bot.send_message            │     │
│  │  Can send alert if: event_type NOT in dict OR now > cooldown[type] │     │
│  └───────────────────────┬────────────────────────────────────────────┘     │
│                          │                                                  │
│                          ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  Queue Wrappers (drop-oldest cap @ 200)                           │     │
│  │                                                                     │     │
│  │  raw_queue ──► BoundedQueue(200) ──► put drops oldest when full  │     │
│  │  result_queue ─► BoundedQueue(200)                                 │     │
│  │  publish_queue─► BoundedQueue(200)                                 │     │
│  │  dlq_queue ────► asyncio.Queue(unbounded, for failed items)       │     │
│  └───────────────────────┬────────────────────────────────────────────┘     │
│                          │                                                  │
│                          ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  Metrics Collector (src/metrics.py or inside SystemState)          │     │
│  │                                                                     │     │
│  │  Daily counters:                                                   │     │
│  │    - drafts_approved, drafts_rejected (→ approve/reject ratio)     │     │
│  │    - json_validation_errors (daily count)                           │     │
│  │    - api_latencies: list[float] (→ hourly P95)                     │     │
│  │                                                                     │     │
│  │  Flush: shutdown → write logs/metrics/YYYY-MM-DD.json              │     │
│  └───────────────────────┬────────────────────────────────────────────┘     │
│                          │                                                  │
│                          ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  Logger Setup (modified logging_setup.py)                         │     │
│  │                                                                     │     │
│  │  - 50MB × 10 rotating file handler                                 │     │
│  │  - Per-module log levels from Config.LOG_LEVELS                    │     │
│  │  - Structured error codes: [ERR_CODE] in message prefix            │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

                    Data flow → alerts → PTB bot → ADMIN_CHAT_ID
                    Data flow → /health → PTB /health handler → admin
                    Data flow → metrics → logs/metrics/YYYY-MM-DD.json
```

### Recommended Project Structure
```
src/
├── health.py              # NEW: HealthCollector, alert cooldown, /health response builder
├── metrics.py             # NEW: DailyMetricsCollector (in-memory counters, file flush)
├── queue_utils.py         # NEW: BoundedQueue (drop-oldest wrapper), DLQ helper
├── logging_setup.py       # MODIFIED: 50MB×10 retention, per-module levels, error codes
├── config.py              # MODIFIED: Add LOG_LEVELS config key, import health setup
├── main.py                # MODIFIED: Create HealthCollector, register modules, wire shutdown
├── ai_handler.py          # MODIFIED: Add cooldown Event, health callback, structured error codes
├── crawler.py             # MODIFIED: Add disconnect detection logging, health callback
├── bot_reviewer.py        # MODIFIED: Add /health command handler alongside /status
├── publisher/consumer.py  # MODIFIED: Add health callback, structured error codes
├── system_state.py        # MODIFIED: Add mode change alert trigger, metrics counters
├── models.py              # MAYBE: Add ErrorCode enum or TypedDict
logs/
├── app.log                # Rotating log file
└── metrics/               # NEW: Daily metrics files
    ├── 2026-05-17.json
    └── 2026-05-18.json
```

### Pattern 1: HealthCollector — Registry with Timeout
**What:** A single `HealthCollector` class that maintains a registry of named health check callbacks. Each module registers a check function during init. The collector runs all checks concurrently with timeout guards.

**When to use:** Central health aggregation point consumed by the `/health` command handler. Keeps health logic out of individual modules.

**Example interface:**
```python
class HealthCollector:
    def __init__(self) -> None:
        self._checks: dict[str, CheckEntry] = {}
        self._alert_cooldowns: dict[str, float] = {}

    def register(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[dict[str, Any]]],
        timeout: float = 5.0,
    ) -> None:
        """Register a module's health check callback."""
        self._checks[name] = CheckEntry(check_fn=check_fn, timeout=timeout)

    async def get_report(self) -> dict[str, Any]:
        """Run all checks concurrently with timeouts. Return aggregated report."""
        async def _run(name: str, entry: CheckEntry) -> tuple[str, Any]:
            try:
                result = await asyncio.wait_for(entry.check_fn(), timeout=entry.timeout)
                return name, {"status": "ok", "data": result}
            except asyncio.TimeoutError:
                return name, {"status": "timeout", "error": f"check timed out after {entry.timeout}s"}
            except Exception as e:
                return name, {"status": "error", "error": str(e)}

        tasks = [_run(name, entry) for name, entry in self._checks.items()]
        results = await asyncio.gather(*tasks)
        report = {"timestamp": datetime.utcnow().isoformat(), "modules": dict(results)}
        # Determine overall status
        all_ok = all(v["status"] == "ok" for _, v in report["modules"].items())
        report["overall"] = "healthy" if all_ok else "degraded"
        return report
```

### Pattern 2: Alert Cooldown — Per-Event-Type Timestamp Tracker
**What:** A dict mapping event types to the last-alerted timestamp. Before sending an alert, check if the event type is in cooldown. Simpler and more correct than TokenBucket for this use case — TokenBucket allows bursty alerts, but first-only-with-cooldown should flatly suppress duplicates.

**When to use:** Any module that needs to send fire-and-forget alerts with dedup. Alert cooldown state lives in `HealthCollector` for central management.

**Example:**
```python
ALERT_COOLDOWN_SECONDS = 1800  # 30 minutes

def can_send_alert(self, event_type: str) -> bool:
    last = self._alert_cooldowns.get(event_type)
    now = time.monotonic()
    if last is None or (now - last) >= ALERT_COOLDOWN_SECONDS:
        self._alert_cooldowns[event_type] = now
        return True
    return False

async def send_alert(self, event_type: str, message: str) -> None:
    if not self.can_send_alert(event_type):
        logger.debug(f"Alert {event_type} suppressed (cooldown active)")
        return
    await self._bot.send_message(chat_id=self._admin_chat_id, text=f"⚠️ {message}")
    logger.info(f"Alert sent: {event_type}")
```

**Key insight:** The cooldown timestamp is stored *at the moment the alert is sent*, not at the moment the condition is detected. This prevents rapid re-triggering when the condition persists.

### Pattern 3: Bounded Queue with Drop-Oldest
**What:** A thin wrapper around `asyncio.Queue` that overrides `put_nowait` to drop the oldest item when at capacity, instead of raising `QueueFull`.

**Why not use `ringq` or `aiodeque`:** These are newer libraries (2026) with no track record. A 15-line wrapper is safer and zero-dependency.

**Example:**
```python
class BoundedQueue(asyncio.Queue):
    """Queue that drops oldest item when put would exceed maxsize."""

    def put_nowait(self, item):
        if self.full():
            # Drop oldest item to make room
            self.get_nowait()
            self.task_done()  # balance the unfinished task counter
            # Log the eviction
            logger.warning("[ERR_QUEUE_OVERFLOW] Queue at capacity — dropped oldest item")
        super().put_nowait(item)

    async def put(self, item):
        # Drop-oldest behavior for async put too (non-blocking is the point)
        self.put_nowait(item)
```

**Note on `task_done()`:** The `BoundedQueue` wrapper must call `task_done()` after evicting to keep the unfinished-task counter consistent. However, if the downstream consumer calls `task_done()` for every `get()`, this can cause a mismatch. A safer approach is to track evictions separately or ensure `task_done()` is only called by consumers. Since the evicted item was never processed, calling `task_done()` is correct — it represents "this work was not done."

**Alternative safer pattern (no wrapper, inline drop-oldest):**
```python
async def put_with_eviction(queue: asyncio.Queue, item):
    """Drop oldest item if queue is full."""
    if queue.full():
        try:
            queue.get_nowait()
            queue.task_done()
        except asyncio.QueueEmpty:
            pass
    await queue.put(item)
```

### Pattern 4: asyncio Event Cooldown — Pause + Auto-Resume
**What:** A second `asyncio.Event` alongside the existing `_shutdown` Event in `AIConsumer`. Workers check both events before processing. When `AllModelsExhausted` is raised, set the pause Event and schedule a timer to clear it after 5 minutes.

**When to use:** AI pause should not conflate with shutdown. The existing shutdown Event terminates workers permanently; the cooldown Event pauses them temporarily.

**Example (additions to `AIConsumer`):**
```python
class AIConsumer:
    def __init__(self, ...):
        ...
        self._shutdown = asyncio.Event()
        self._pause = asyncio.Event()      # NEW: NOT set = not paused
        # Workers check both: not shutdown AND not paused
        self._pause.clear()  # Start unpaused (already default)
        self._pause_cooldown_task: asyncio.Task | None = None

    async def pause_ai(self, duration: int = 300) -> None:
        """Pause AI processing for `duration` seconds."""
        self._pause.set()
        logger.critical("[ERR_ALL_MODELS_EXHAUSTED] All AI models exhausted — pausing %d seconds", duration)
        self._pause_cooldown_task = asyncio.create_task(self._auto_resume(duration))

    async def _auto_resume(self, duration: int) -> None:
        await asyncio.sleep(duration)
        self._pause.clear()
        logger.info("AI cooldown expired — resuming processing")

    async def _worker(self, worker_id: int) -> None:
        while not self._shutdown.is_set():
            if self._pause.is_set():
                await asyncio.sleep(1)  # Check every second while paused
                continue
            # ... existing processing logic ...
```

**Trigger point:** In `call_structured()` or `call_with_fallback()`, when `AllModelsExhausted` is caught:
```python
except AllModelsExhausted:
    await ai_consumer.pause_ai(300)  # 5-minute cooldown
```

### Pattern 5: Config-Driven Per-Module Log Levels
**What:** A dict in config mapping logger names to log level strings. At startup, apply these via `logging.getLogger(name).setLevel(level)`.

**Config format (in `.env` or dedicated config key):**
```
# .env
LOG_LEVELS={"src.crawler": "DEBUG", "src.ai_handler": "INFO", "src.publisher": "WARNING"}
```

**Implementation (in `logging_setup.py`):**
```python
def apply_module_levels(levels_config: dict[str, str] | None) -> None:
    """Set per-module log levels from config dict."""
    if not levels_config:
        return
    for logger_name, level_name in levels_config.items():
        level = getattr(logging, level_name.upper(), None)
        if level is None:
            logger.warning("Invalid log level '%s' for logger '%s'", level_name, logger_name)
            continue
        logging.getLogger(logger_name).setLevel(level)
        logger.info("Set %s log level to %s", logger_name, level_name)
```

**Key insight:** Python's logging hierarchy means setting `src.ai_handler` also affects `src.ai_handler.OpenRouterClient` (children inherit parent settings unless overridden). This simplifies config — you typically only need to set levels for top-level module names.

### Pattern 6: Structured Error Codes
**What:** Prefix-based error codes in log messages for grep-ability. A central registry (dict or enum) ensures consistency.

**Example registry:**
```python
from enum import Enum

class ErrorCode(str, Enum):
    QUEUE_OVERFLOW = "ERR_QUEUE_OVERFLOW"
    ALL_MODELS_EXHAUSTED = "ERR_ALL_MODELS_EXHAUSTED"
    PUBLISH_FAIL = "ERR_PUBLISH_FAIL"
    SOURCE_DISCONNECT = "ERR_SOURCE_DISCONNECT"
    JSON_VALIDATION_FAIL = "ERR_JSON_VALIDATION_FAIL"
    BINANCE_LIMIT = "ERR_BINANCE_DAILY_LIMIT"
    BOT_PERMISSION = "ERR_BOT_PERMISSION"

def ec(code: ErrorCode, message: str) -> str:
    return f"[{code.value}] {message}"

# Usage
logger.error(ec(ErrorCode.QUEUE_OVERFLOW, "raw_queue at capacity — dropped oldest item"))
```

### Pattern 7: Daily Metrics Aggregation
**What:** An in-memory metrics collector that accumulates counters throughout the day and flushes to a JSON file on shutdown.

**Example:**
```python
import json
from pathlib import Path
from datetime import date
from collections import defaultdict

class DailyMetrics:
    def __init__(self, metrics_dir: Path = Path("logs/metrics")):
        self.metrics_dir = metrics_dir
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self._counters: dict[str, int] = defaultdict(int)
        self._latencies: list[float] = []

    def increment(self, key: str) -> None:
        self._counters[key] += 1

    def record_latency(self, seconds: float) -> None:
        self._latencies.append(seconds)

    def flush(self) -> None:
        """Write current day's metrics to file."""
        today = date.today().isoformat()  # "2026-05-17"
        filepath = self.metrics_dir / f"{today}.json"

        metrics = {
            "date": today,
            "counters": dict(self._counters),
        }
        if self._latencies:
            sorted_lat = sorted(self._latencies)
            n = len(sorted_lat)
            metrics["api_latency_p95"] = sorted_lat[int(n * 0.95)]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        logger.info("Daily metrics flushed to %s", filepath)

    def approve_reject_ratio(self) -> float | None:
        approved = self._counters.get("drafts_approved", 0)
        rejected = self._counters.get("drafts_rejected", 0)
        total = approved + rejected
        if total == 0:
            return None
        return approved / total
```

**Integration with shutdown:** Call `daily_metrics.flush()` in the main `shutdown()` handler. Add a periodic timer (every N minutes) as safety net:

```python
async def periodic_flush(self, interval: int = 300) -> None:
    while True:
        await asyncio.sleep(interval)
        self.flush()
```

### Pattern 8: Simple In-Memory DLQ
**What:** A separate `asyncio.Queue` that receives messages that failed permanently. Admin can inspect via `/health` and trigger manual retry.

**Example:**
```python
class DeadLetterQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._count: int = 0

    async def put(self, item) -> None:
        await self._queue.put(item)
        self._count += 1
        logger.warning("[ERR_DLQ] Item added to DLQ — total: %d", self._count)

    async def get(self):
        item = await self._queue.get()
        self._count -= 1
        return item

    def snapshot(self) -> dict:
        """For /health display."""
        return {"depth": self._queue.qsize(), "total_accumulated": self._count}

    async def retry_all(self, target_queue: asyncio.Queue) -> int:
        """Re-queue all DLQ items to target queue for retry."""
        count = 0
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                await target_queue.put(item)
                self._queue.task_done()
                count += 1
            except asyncio.QueueEmpty:
                break
        self._count = self._queue.qsize()
        return count
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Queue with drop-oldest | Custom asyncio.Queue subclass | `BoundedQueue` wrapper (15 lines) | asyncio.Queue `maxsize` blocks instead of dropping — wrong behavior for unbounded memory protection |
| Alert rate limiting | TokenBucket (buckshot) | `dict[str, float]` timestamp tracker | TokenBucket allows bursts; first-only cooldown means flat suppression. Simpler is correct |
| Per-module log levels | Custom logging framework | `logging.getLogger(name).setLevel()` | Python's logging hierarchy already supports this perfectly — no reason to reinvent |
| Error code formatting | String constants scattered in files | `ErrorCode(str, Enum)` | Scattered strings inevitably diverge. Enum gives grep-ability + autocomplete + validation |
| Async health check timeout | Manual `asyncio.wait_for()` per check | Already built into `asyncio.wait_for()` | Don't wrap it — just use it. Pass individual timeouts per check |
| Metrics file path construction | Manual date string formatting | `date.today().isoformat()` | ISO 8601 date naturally sorts as strings. Path construction is a one-liner |

**Key insight:** Every pattern in this phase maps to a 5-20 line stdlib solution. The risk is over-engineering — writing a framework when a dict + a function suffices. Resist the urge.

---

## State of the Art

| Old Approach | Current Approach | Changed When | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded log levels in `logging_setup.py` | Config-driven per-module levels from `LOG_LEVELS` env var | Phase 5 | Enables debugging individual modules without restarting entire pipeline |
| `logger.error("queue full")` | `logger.error("[ERR_QUEUE_OVERFLOW] ...")` | Phase 5 | Grep-filterable error codes; future alert routing can parse prefix |
| Unbounded queues | `BoundedQueue` with 200-item cap | Phase 5 | Prevents memory exhaustion under sustained load |
| Silent failures (source disconnect, all models exhausted) | Fire-and-forget alert to admin via PTB | Phase 5 | Admin knows about failures within seconds of detection |
| Manual health checking (admin had to guess) | `/health` command with per-module status | Phase 5 | Instant system introspection without log spelunking |

---

## Common Pitfalls

### Pitfall 1: `task_done()` Mismatch in Evicting Queue
**What goes wrong:** When a `BoundedQueue` drops the oldest item, it calls `task_done()` to balance the internal counter. But if the consumer also calls `task_done()` for each `get()`, the counter goes negative, causing `join()` to never complete or raising `ValueError`.

**Root cause:** `asyncio.Queue` maintains an internal `_unfinished_tasks` counter — incremented on `put()`, decremented on `task_done()`. Evicted items were never processed, so calling `task_done()` is semantically correct, but the counter state depends on the order of evictions vs. consumer `task_done()` calls.

**How to avoid:** Two options:
1. **Track evictions via a separate counter:** Override `put_nowait()` to return a sentinel indicating whether eviction occurred. Don't call `task_done()` in the wrapper at all — instead, let the consumer manage the counter.
2. **Simpler approach:** Don't use `task_done()` / `join()` pattern with evicting queues. Since `join()` is not used anywhere in the current codebase (all modules use a simple `while not shutdown` pattern), this isn't an issue for this project.

**Warning signs:** `Queue.join()` hangs, or `task_done()` raises `ValueError` ("too many calls to 'task_done'").

### Pitfall 2: Alert Storm on Startup
**What goes wrong:** On first startup, all cooldown timestamps are `None`, so every module's initial health check can trigger alerts simultaneously. Admin gets 5+ alerts in 2 seconds.

**Root cause:** `can_send_alert()` returns `True` for all event types on first call because the cooldown dict is empty.

**How to avoid:** Initialize all expected alert event types with `time.monotonic()` at collector creation time. This gives them an implicit cooldown from the collector's birth:

```python
def __init__(self):
    self._alert_cooldowns = {
        "source_disconnect": time.monotonic(),
        "all_models_exhausted": time.monotonic(),
        "queue_overflow": time.monotonic(),
        "binance_daily_limit": time.monotonic(),
        "publisher_permanent_error": time.monotonic(),
    }
```

### Pitfall 3: Stale Metrics on Crash
**What goes wrong:** If the process crashes (SIGKILL, power loss), the in-memory daily metrics are lost. The `flush()` method only runs in the graceful shutdown handler.

**Root cause:** In-memory counters with flush-on-shutdown are inherently vulnerable to crashes.

**How to avoid:** Two mitigations:
1. **Periodic flush:** Run a background task that flushes every N minutes (e.g., 5 min). If the system was up for 4 hours and crashed, you lose at most 5 minutes of data.
2. **Accept the risk:** For v1 metrics (approve/reject ratio, validation errors), daily aggregates are informative even if a partial day is lost. Document this limitation.

The periodic flush approach is recommended — it's 3 lines of code and dramatically reduces data loss.

### Pitfall 4: Log Level Config Can't Relax Already-Logged Messages
**What goes wrong:** Setting `LOG_LEVELS={"src.crawler": "DEBUG"}` does NOT retroactively print messages that were already suppressed by the root logger's level. The root logger is set to `DEBUG` already (in the current config), so this isn't an issue in the current pipeline. But if the root level were raised, module-level settings could be confusing.

**Root cause:** Logger level is checked at each logger in the hierarchy. If parent is `WARNING` and child is `DEBUG`, the child's `DEBUG` messages pass, but the parent might still drop them depending on handler configuration.

**How to avoid:** Ensure the root logger is at least as permissive as the most permissive module level. With the current setup (root = `DEBUG`), this is already correct.

### Pitfall 5: Health Check Timeouts Blocking the Event Loop
**What goes wrong:** If a health check callback does synchronous I/O (e.g., reading a file with `open().read()`), it blocks the event loop for all concurrent tasks.

**Root cause:** Health checks are run inside `asyncio.gather()`, which expects all callbacks to be async. A sync callback blocks the event loop.

**How to avoid:** Enforce async-only check functions. Document that all registered check functions must be `async def`. For the rare case where a sync operation is unavoidable, use `asyncio.to_thread()`:

```python
async def check_disk_space() -> dict:
    usage = await asyncio.to_thread(shutil.disk_usage, "/")
    return {"free_gb": usage.free / 1e9}
```

---

## Code Examples

### HealthCollector Full Implementation

```python
"""src/health.py — Health check registry + alert cooldown management."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

ALERT_COOLDOWN_SECONDS = 1800  # 30 minutes

HealthCheckFn = Callable[[], Awaitable[dict[str, Any]]]


@dataclass
class CheckEntry:
    check_fn: HealthCheckFn
    timeout: float = 5.0


class HealthCollector:
    """Registry-based health check collector with alert cooldown."""

    def __init__(self, alert_cooldown: float = ALERT_COOLDOWN_SECONDS) -> None:
        self._checks: dict[str, CheckEntry] = {}
        self._alert_cooldowns: dict[str, float] = {}
        self._alert_cooldown_duration = alert_cooldown
        self._bot = None  # Set via set_bot(bot, admin_chat_id)
        self._admin_chat_id: str | None = None

    def set_bot(self, bot, admin_chat_id: str) -> None:
        """Wire PTB bot for alert delivery (called from main.py)."""
        self._bot = bot
        self._admin_chat_id = admin_chat_id

    def register(self, name: str, check_fn: HealthCheckFn, timeout: float = 5.0) -> None:
        """Register a module health check callback."""
        if name in self._checks:
            logger.warning("Health check '%s' already registered — overwriting", name)
        self._checks[name] = CheckEntry(check_fn=check_fn, timeout=timeout)
        logger.info("Health check registered: %s (timeout=%ss)", name, timeout)

    def can_send_alert(self, event_type: str) -> bool:
        """Check if alert can be sent (cooldown not active)."""
        last = self._alert_cooldowns.get(event_type)
        now = time.monotonic()
        if last is None or (now - last) >= self._alert_cooldown_duration:
            self._alert_cooldowns[event_type] = now
            return True
        return False

    async def send_alert(self, event_type: str, message: str) -> None:
        """Send fire-and-forget alert to admin (with dedup cooldown)."""
        if not self.can_send_alert(event_type):
            logger.debug("Alert '%s' suppressed (cooldown active)", event_type)
            return
        logger.info("Sending alert '%s': %s", event_type, message)
        if self._bot is None:
            logger.warning("Bot not wired — cannot send alert: %s", message)
            return
        try:
            await self._bot.send_message(
                chat_id=self._admin_chat_id,
                text=f"⚠️ {message}",
            )
        except Exception:
            logger.exception("Failed to send alert '%s'", event_type)

    async def get_report(self) -> dict[str, Any]:
        """Run all health checks concurrently. Return aggregated report."""
        async def _run_check(name: str, entry: CheckEntry) -> tuple[str, dict[str, Any]]:
            try:
                data = await asyncio.wait_for(entry.check_fn(), timeout=entry.timeout)
                return name, {"status": "ok", "data": data}
            except asyncio.TimeoutError:
                return name, {"status": "timeout", "error": f"timed out after {entry.timeout}s"}
            except Exception as e:
                return name, {"status": "error", "error": str(e)}

        tasks = [_run_check(name, entry) for name, entry in self._checks.items()]
        results = await asyncio.gather(*tasks)

        modules = dict(results)
        all_ok = all(v["status"] == "ok" for v in modules.values())
        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "overall": "healthy" if all_ok else "degraded",
            "modules": modules,
        }
        return report
```

### Module Health Check Registration (per-module pattern)

```python
# In crawler.py
class TelegramCrawler:
    def register_health(self, health_collector: HealthCollector) -> None:
        health_collector.register("crawler", self._check_health, timeout=3.0)

    async def _check_health(self) -> dict:
        """Return crawler health status."""
        return {
            "connected": self.client.is_connected(),
            "channels_monitored": len(self.sources),
            "last_message_received": getattr(self, "_last_message_time", None),
        }

# In ai_handler.py
class AIConsumer:
    def register_health(self, health_collector: HealthCollector) -> None:
        health_collector.register("ai_handler", self._check_health, timeout=3.0)

    async def _check_health(self) -> dict:
        """Return AI handler health status."""
        return {
            "active_workers": sum(1 for w in self._workers if not w.done()),
            "worker_count": self.worker_count,
            "paused": self._pause.is_set(),
            "cooldown_remaining": self._cooldown_remaining(),
            "last_processed_at": getattr(self, "_last_processed_time", None),
        }

    def _cooldown_remaining(self) -> int | None:
        if not self._pause.is_set():
            return None
        # Return seconds remaining if paused
        return max(0, self._pause_until - time.monotonic()) if hasattr(self, "_pause_until") else None

# In publisher/consumer.py
class PublisherConsumer:
    def register_health(self, health_collector: HealthCollector) -> None:
        health_collector.register("publisher", self._check_health, timeout=5.0)

    async def _check_health(self) -> dict:
        return {
            "last_publish_at": getattr(self, "_last_publish_time", None),
            "last_publish_success": getattr(self, "_last_publish_success", None),
            "processed_total": len(self._published_ids),
        }
```

### `/health` Command Handler (in bot_reviewer.py additions)

```python
async def health(update: Update, context: CallbackContext) -> None:
    """Handle /health command."""
    health_collector: HealthCollector = context.application.bot_data["health_collector"]
    report = await health_collector.get_report()

    lines = [f"🩺 **System Health** [{report['overall'].upper()}]"]
    lines.append(f"Checked: {report['timestamp']}")
    lines.append("")

    for module, status in report["modules"].items():
        emoji = "✅" if status["status"] == "ok" else ("⏱️" if status["status"] == "timeout" else "❌")
        lines.append(f"{emoji} **{module}**: {status['status']}")
        if "data" in status:
            for key, value in status["data"].items():
                if value is not None:
                    lines.append(f"  • {key}: {value}")
        if "error" in status:
            lines.append(f"  • error: {status['error']}")

    await update.message.reply_text("\n".join(lines))
```

### `main.py` Integration Wiring

```python
# In main():
health_collector = HealthCollector()

# After creating all modules:
crawler.register_health(health_collector)
ai_consumer.register_health(health_collector)
# Publisher consumer gets health collector injected

# Wire into bot_data for /health command:
# (pass health_collector through bot_data so bot_reviewer can register /health)

# In shutdown():
daily_metrics.flush()
```

### Daily Latency P95 Calculation

```python
def calculate_p95(latencies: list[float]) -> float | None:
    """Calculate P95 from a list of API latencies in seconds."""
    if not latencies:
        return None
    sorted_lat = sorted(latencies)
    idx = int(len(sorted_lat) * 0.95)
    return sorted_lat[idx]
```

### Queue Depth Snapshot (D-17 pattern)

```python
async def log_queue_depths(raw_queue, result_queue, publish_queue) -> None:
    """Log queue depths at regular intervals."""
    while True:
        logger.info(
            "Queue depths — raw: %d, result: %d, publish: %d",
            raw_queue.qsize(),
            result_queue.qsize(),
            publish_queue.qsize(),
        )
        await asyncio.sleep(300)  # every 5 minutes
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `asyncio.Queue.full()` returns `True` when queue size equals `maxsize` | Pattern 3 | Verified via Python docs [http://docs.python.org/library/asyncio-queue.html]. No risk — this is documented behavior |
| A2 | `time.monotonic()` is monotonic (never decreases) even across system clock adjustments | Pattern 2 | Verified via Python docs. Essential for correct cooldown behavior |
| A3 | Python logging hierarchy propagates level checks from child to parent | Pattern 5 | Verified via Python docs. If this were wrong, per-module levels might not filter correctly |
| A4 | PTB `bot.send_message()` is always async and safe to call from outside a handler | Alert | Verified via PTB docs. If wrong, alerts inside synchronous code paths could block |
| A5 | `asyncio.wait_for()` raises `asyncio.TimeoutError` (not `concurrent.futures.TimeoutError`) | Pattern 1 | Verified via Python docs. If wrong, timeout catches would miss the exception |

**Note:** All assumptions marked as LOW risk because they rely on documented Python stdlib behavior.

---

## Open Questions (RESOLVED)

1. **Where to put `alert_cooldown` timers?**
   - **What we know:** CONTEXT.md says D-03 and "cooldown timer location (HealthCollector vs per-module)" is at the agent's discretion
   - **What's unclear:** Whether each module manages its own cooldown timestamps or HealthCollector does it centrally
   - **Recommendation:** HealthCollector manages all alert cooldowns centrally. This keeps the dedup logic in one place, makes it easy to inspect/dump via `/health`, and avoids each module needing its own timer infrastructure. The tradeoff is HealthCollector needs to know about all event types at startup (initialize all timestamps to prevent startup alert storm).
   - **RESOLVED:** Plan 01 implements HealthCollector with centralized `_alert_cooldowns` dict and per-event-type initialization at construction time. All 5 event types pre-seeded with `time.monotonic()` to prevent startup alert storm.

2. **DLQ retry mechanism — how should admin trigger retry?**
   - **What we know:** D-09 says admin can manually retry failed items. CONTEXT.md says simple counter/message-id list exposed via /health rather than full message persistence
   - **What's unclear:** What's the admin-facing retry command? `/dlq_retry`? And should retried items go back to the original queue or be re-processed?
   - **Recommendation:** Add `/dlq_retry` command handler in bot_reviewer.py. When invoked, re-queue all DLQ items to the top of the original queue. Keep item IDs in DLQ for admin inspection. Admin sees DLQ depth in `/health` and decides when to retry. Non-urgent — can be a follow-up enhancement if v1 DLQ is "fire and forget."
   - **RESOLVED:** Plan 02 implements DLQ with `snapshot()` for /health exposure and `retry_all()` for programmatic retry. The `/dlq_retry` command handler is deferred — Plan 06 wires the admin-facing retry command.

3. **Queue depth >50 → auto-switch to MANUAL. How to detect which queue?**
   - **What we know:** D-07 says queue depth >50 triggers auto-switch + alert. There are 3 queues (raw, result, publish)
   - **What's unclear:** Does ANY queue >50 trigger switch? Or is it publish_queue (draft review queue) specifically? The original AI-SPEC §9.2 says "Queue depth >50 → auto switch to MANUAL mode" which likely refers to the draft review queue (result_queue)
   - **Recommendation:** Check result_queue depth (drafts pending review). Switch to MANUAL + send alert. This prevents admin from being overwhelmed by pending reviews. The raw_queue and publish_queue are pipeline buffers, not decision bottlenecks. Add queue depth monitoring to the consumer's existing backpressure check (qsize() > 10 already logged — extend to check > 50 for mode switch).
   - **RESOLVED:** Plan 06 implements result_queue depth check >50 triggering auto-switch to MANUAL mode + alert via HealthCollector. Raw_queue and publish_queue excluded from the trigger — they are pipeline buffers, not decision bottlenecks.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.11+ | All patterns (asyncio, `Task` cancellation) | ✓ | 3.11+ | — |
| `logging` stdlib | Config-driven levels, rotating file handler | ✓ (stdlib) | — | — |
| `asyncio` stdlib | BoundedQueue, Event cooldown, async wait_for | ✓ (stdlib) | — | — |
| `time` stdlib | Alert cooldown (monotonic), latency timing | ✓ (stdlib) | — | — |
| `json` stdlib | Metrics file serialization | ✓ (stdlib) | — | — |
| `pathlib` stdlib | Metrics/log directory creation | ✓ (stdlib) | — | — |
| `python-telegram-bot` | Alert delivery, /health command | ✓ (exists) | — | — |
| `httpx` | API latency tracking | ✓ (exists) | — | — |

**Missing dependencies with no fallback:** None — all patterns use stdlib or existing project dependencies.

**Missing dependencies with fallback:** None — zero new packages required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | Not found — may inherit from project defaults |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| HEALTH-01 | HealthCollector runs registered callbacks concurrently | unit | `pytest tests/test_health.py::test_collector_runs_all_checks -x` |
| HEALTH-02 | HealthCollector timeout isolates unresponsive callback | unit | `pytest tests/test_health.py::test_check_timeout -x` |
| HEALTH-03 | Alert cooldown suppresses duplicates within window | unit | `pytest tests/test_health.py::test_alert_cooldown -x` |
| HEALTH-04 | BoundedQueue drops oldest when full | unit | `pytest tests/test_queue_utils.py::test_bounded_queue_eviction -x` |
| HEALTH-05 | AIConsumer pause Event stops workers, auto-resumes | integration | `pytest tests/test_ai_handler.py::test_pause_cooldown -x` |
| HEALTH-06 | Per-module log levels are applied correctly | unit | `pytest tests/test_logging_setup.py::test_module_levels -x` |
| HEALTH-07 | Daily metrics file written on shutdown | integration | `pytest tests/test_metrics.py::test_flush_on_shutdown -x` |
| HEALTH-08 | Queue depth >50 triggers mode switch + alert | integration | `pytest tests/test_health.py::test_queue_depth_alert -x` |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_health.py tests/test_queue_utils.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_health.py` — covers HEALTH-01, HEALTH-02, HEALTH-03, HEALTH-08
- [ ] `tests/test_queue_utils.py` — covers HEALTH-04
- [ ] `tests/test_ai_handler.py` — add `test_pause_cooldown` for HEALTH-05
- [ ] `tests/test_logging_setup.py` — covers HEALTH-06
- [ ] `tests/test_metrics.py` — covers HEALTH-07
- [ ] `tests/conftest.py` — shared fixtures (mock PTB bot, HealthCollector with wired bot)
- [ ] Framework install: `pip install pytest pytest-asyncio` — if not detected

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `/health` command output must not leak sensitive info (API keys, tokens, internal paths) |
| V7 Logging & Monitoring | yes | Structured logging with error codes; config-driven log levels; metrics aggregation |

### Known Threat Patterns for This Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Health endpoint leaks credentials | Information Disclosure | `/health` response must explicitly exclude: API keys, tokens, file paths, IPs |
| Log injection | Tampering | Structured error codes are prefixes, not user-controlled input. Avoid logging unvalidated message content at ERROR level |
| Metrics file overwrite | Tampering | Write-once pattern: if `YYYY-MM-DD.json` exists, merge counters rather than overwrite |
| Alert suppression via cooldown exhaustion | Denial of Service | Cooldowns reset after 30 min regardless of alert count. Mix of alert types ensures at least one path is available |
| Bot token exposure in alert messages | Information Disclosure | Alert messages must never include the bot token. Use generic references like "delivery system" |

**Key security principle for this phase:** ALL `/health` output and ALL alert messages must be audited for information leaks before going to production. A `/health` command should tell the admin "what's happening" but never "what credentials exist" or "where files live."

---

## Sources

### Primary (HIGH confidence) — Python stdlib documentation
- Python docs `asyncio.Queue` — queue behavior, full(), maxsize semantics [http://docs.python.org/library/asyncio-queue.html]
- Python docs `logging` — hierarchy, setLevel propagation [https://docs.python.org/3/library/logging.html]
- Python docs `asyncio.Event` — event loop coordination [https://docs.python.org/3/library/asyncio-sync.html]
- Python docs `time.monotonic()` — monotonic clock guarantees [https://docs.python.org/3/library/time.html]
- Python docs `asyncio.wait_for()` — timeout semantics [https://docs.python.org/3/library/asyncio-task.html]

### Primary (HIGH confidence) — Codebase verification
- `src/ai_handler.py` — Verified existing `asyncio.Event` shutdown pattern, `AIConsumer` worker lifecycle
- `src/logging_setup.py` — Verified current `RotatingFileHandler` config (10MB × 5, console INFO + file DEBUG)
- `src/bot_reviewer.py` — Verified existing `send_message` pattern for alert reuse, `/status` command handler
- `src/system_state.py` — Verified singleton pattern with `asyncio.Lock` for thread-safe state management
- `src/main.py` — Verified queue creation, module wiring, signal handler + shutdown orchestration
- `src/publisher/consumer.py` — Verified `asyncio.Event` shutdown pattern, publish consumer lifecycle

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all Python stdlib, already verified in codebase
- Architecture: HIGH — patterns are well-known async Python idioms
- Pitfalls: HIGH — derived from documented stdlib behavior and common async mistakes
- Error code design: MEDIUM — exact code strings are at the agent's discretion per CONTEXT.md

**Research date:** 2026-05-17
**Valid until:** Indefinite (Python stdlib behavior doesn't change; patterns are version-independent)
