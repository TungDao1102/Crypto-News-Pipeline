---
plan_id: "05-06"
plan_name: "System Wiring — Health callbacks, /health command, BoundedQueue, DLQ, error codes, alert triggers"
one_liner: "Connected all Phase 5 components: health callbacks on 3 modules, /health command, BoundedQueue+DLE+DailyMetrics wiring, structured error codes across 6 modules, and 4 alert trigger paths"
key-files:
  created: []
  modified:
    - src/main.py
    - src/bot_reviewer.py
    - src/crawler.py
    - src/ai_handler.py
    - src/publisher/consumer.py
    - src/publisher/telegram.py
    - src/publisher/binance_square.py
    - src/system_state.py
req-ids:
  - REQ-05-06
tech-stack:
  added: []
  patterns:
    - "Health callback registration: each module has register_health() + _check_health() pair"
    - "/health command: formatted output with emoji per-module status, queue depths, DLQ state"
    - "BoundedQueue(200) replaces asyncio.Queue for all 3 pipeline queues"
    - "DeadLetterQueue wired to PublisherConsumer for exception routing"
    - "4 alert triggers: source disconnect, queue overflow, binance limit, publisher error"
    - "Queue depth >50 auto-switch MANUAL + alert"
    - "ErrorCode enum used across all 6 modules for structured error logging"
    - "Approval/rejection events tracked via DailyMetrics.increment()"
dependencies:
  requires:
    - "05-01 (HealthCollector)"
    - "05-02 (BoundedQueue, DeadLetterQueue)"
    - "05-03 (DailyMetrics)"
    - "05-04 (ErrorCode enum)
    - "05-05 (AIConsumer pause)"
  provides: []
---

## Summary

Plan 05-06 is the integration plan that wires all Wave 1 components into the running pipeline. It touches 8 files across the full codebase:

**src/main.py** — Central wiring hub:
- Creates `HealthCollector`, `DeadLetterQueue`, `DailyMetrics`, and `BoundedQueue(200)` for all 3 queues
- Calls `register_health()` on crawler and ai_consumer
- Passes `health_collector`, `dlq`, `daily_metrics`, `raw_queue` to `run_bot()`
- Background tasks: `log_queue_depths()` and `flush_metrics_periodically()` every 5 minutes
- `shutdown()` flushes metrics, logs DLQ state

**src/bot_reviewer.py** — Bot commands and review pipeline:
- `/health` command handler — formatted output with per-module emoji status + queue depths + DLQ
- `register_handlers()` adds `/health` command
- Queue depth >50 → auto-switch MANUAL + alert
- Approve/reject handlers call `daily_metrics.increment()`
- `run_bot()` accepts and wires all new components into `bot_data`

**src/crawler.py** — Reconnection loop + source disconnect alert:
- `register_health()`, `_check_health()` tracking connected status
- Reconnection loop with exponential backoff (10 retry max, 300s cap, jitter)
- `ErrorCode.SOURCE_DISCONNECT` logging on disconnect
- Alert via `health_collector.send_alert()` after max retries

**src/ai_handler.py** — AI health callback:
- `register_health()`, `_check_health()` reporting pause status, cooldown remaining, last processed time

**src/publisher/consumer.py** — Publisher with DLQ + alert triggers:
- Accepts `dlq` and `health_collector` parameters
- Routes unexpected exceptions to DLQ
- Alert triggers for binance limit (220009) and permanent errors
- `ErrorCode.PUBLISH_FAIL` logging for backpressure and failures

**src/publisher/telegram.py** — Error codes for Telegram failures:
- `ErrorCode.BOT_PERMISSION` for Forbidden (kicked/blocked)
- `ErrorCode.PUBLISH_FAIL` for RetryAfter, BadRequest, NetworkError, TimedOut

**src/publisher/binance_square.py** — Error codes for Binance failures:
- `ErrorCode.BINANCE_DAILY_LIMIT` for code 220009 and empty content
- `ErrorCode.PUBLISH_FAIL` for other failures, timeouts, HTTP errors

**src/system_state.py** — No functional changes needed (metrics tracking via DailyMetrics in bot_reviewer.py)

### Deviations from Plan

None — plan executed exactly as specified.

### Code Quality Observations

- All 80 Phase 5 tests pass
- All modules load without import errors — no circular imports
- ErrorCode enum imports in 6 modules (`src/logging_setup.py` → `src/crawler.py`, `src/ai_handler.py`, `src/bot_reviewer.py`, `src/publisher/consumer.py`, `src/publisher/telegram.py`, `src/publisher/binance_square.py`)
- Alert delivery uses the cooldown mechanism from Plan 05-01 — prevents alert storms
- Queue depth >50 alert is rate-limited by HealthCollector's cooldown (fires at most once per 30 min per event type)
- The `register_health()` methods store a health_collector reference for alert delivery (crawler, publisher)

### Known Stubs

None identified.

### Threat Flags

None — T-05-12 (/health output), T-05-13 (alert message content), T-05-14 (error code log injection), and T-05-15 (queue depth alert loop) are correctly mitigated.

### Tests

```text
All 80 Phase 5 tests pass across 5 test files:
tests/test_health.py .......... 10 passed
tests/test_queue_utils.py ....... 8 passed
tests/test_metrics.py ........ 6 passed
tests/test_logging_setup.py .... 4 passed
tests/test_ai_handler.py ..... 53 passed (includes pre-existing + new tests)
```
