# Phase 5: Resilience, Logging & Monitoring - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add failure detection, alerting, health introspection, queue overflow handling, structured logging, and daily metrics across all 4 prior pipeline stages (crawler, AI handler, bot reviewer, publisher). No new features — only hardening of existing infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Alert Delivery & Health Command
- **D-01:** Alerts delivered via existing PTB bot `send_message` to `ADMIN_CHAT_ID` (reuse D-01 from Phase 3). Plus a `/health` command for on-demand status.
- **D-02:** Alert triggers (all fire-and-forget push alerts): source disconnect after max retries, queue depth >50 critical, Binance daily limit (220009), publisher permanent errors (Binance ban codes, Telegram bot removed from channel).
- **D-03:** Alert dedup: first-only per event type with 30-minute cooldown window. Prevents alert storms during cascading failures.
- **D-04:** `/health` command shows per-module status + timestamps (crawler: connected/disconnected/last msg, AI: active workers/last processed, publisher: last publish/per-platform status, all queue depths).
- **D-05:** Auto-pause AI processing only on `AllModelsExhausted`. Pause for 5 minutes, resume automatically via cooldown timer. Source disconnect does NOT pause AI — it can drain queued messages.
- **D-06:** `/health` implemented as standalone `HealthCollector` module (`src/health.py`). Each module registers a health check callback. Clean separation from `SystemState`.

### Queue Auto-Mitigation & Overflow
- **D-07:** Queue depth >50 → auto-switch to MANUAL mode + alert sent. Admin must manually switch back to AUTO via `/mode_auto`. No admin confirmation prompt.
- **D-08:** Hard cap of 200 items per queue (`raw_queue`, `result_queue`, `publish_queue`). Drop oldest when exceeded. Prevents unbounded memory growth.
- **D-09:** Simple in-memory dead-letter queue (`asyncio.Queue`) for persistently failing messages. Inspectable via `/health`. Admin can manually retry failed items.
- **D-10:** Auto-pause mechanism: `asyncio.Event` + cooldown timer inside `AIConsumer`. Workers check the Event before processing. Reuses existing shutdown Event pattern. Not conflated with rate limiter.

### Logging Format & Levels
- **D-11:** Keep human-readable log format only. No JSON logging (no log aggregation pipeline to consume it).
- **D-12:** Config-driven per-module log levels via `LOG_LEVELS` config (JSON dict, env var or config key). Each module sets its own level independently.
- **D-13:** Structured error codes prefixed in log messages: `[ERR_QUEUE_OVERFLOW]`, `[ERR_ALL_MODELS_EXHAUSTED]`, `[ERR_PUBLISH_FAIL]`, `[ERR_SOURCE_DISCONNECT]`, etc. Enables grep-based filtering and future alert routing.
- **D-14:** Increased log retention: 50MB per file × 10 backups (was 10MB × 5). Gives more history for debugging.

### Metrics Tracking
- **D-15:** v1 metrics: approve/reject ratio (daily), JSON validation errors (daily count), API latency P95 (hourly). Queue depth time-series deferred — snapshot to log file as lightweight alternative.
- **D-16:** Metrics surfaced both ways: daily aggregate file (`logs/metrics/YYYY-MM-DD.json`) for historical record, AND extended `/status` command for quick glance.
- **D-17:** Queue depth snapshots logged at intervals via existing `logger.info` — no dedicated metrics file for queue depth in v1.
- **D-18:** Daily metrics are per-day aggregates (end-of-day rollup), not per-event append.

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### System Architecture & Resilience
- `AI-SPEC.md` §3 — Data flow architecture, queue relationships (ingestion → processing → distribution)
- `AI-SPEC.md` §4 — Module structure, module responsibilities
- `AI-SPEC.md` §6 — Full resilience strategy: Telethon exponential backoff, OpenRouter fallback chain, structured outputs, logging & monitoring
- `AI-SPEC.md` §6.2 — Model fallback chain and "alert admin + pause 5 min" on all models exhausted
- `AI-SPEC.md` §6.4 — Logging & Monitoring: rotating file handler, log levels mapping per event type
- `AI-SPEC.md` §9 — Guardrails: online (content/duplicate/scam/rate limit) + offline metrics
- `AI-SPEC.md` §9.2 — Offline metrics specification: approve/reject ratio, JSON error %, API latency P95, queue depth

### Existing Code
- `src/main.py` — Entry point with signal handler, queue creation, module wiring
- `src/logging_setup.py` — Current RotatingFileHandler config (10MB × 5, console INFO + file DEBUG)
- `src/system_state.py` — SystemState singleton (mode, processed count, asyncio.Lock)
- `src/ai_handler.py` — AIConsumer (queue consumer, shutdown Event, worker lifecycle, backpressure logging), TokenBucket, AllModelsExhausted exception
- `src/crawler.py` — TelegramCrawler, exponential backoff constants (1s→300s, ×2, jitter 0.1, max 10 retries)
- `src/bot_reviewer.py` — PTB bot wiring, publish_queue consumer, /status command
- `src/models.py` — DraftContent, PublishResult, RawMessage models

### Prior Phase Contracts
- `.planning/phases/04-publisher/04-CONTEXT.md` — D-04 partial failure handling, error logging patterns, Binance error code mapping
- `.planning/phases/03-bot-reviewer/03-CONTEXT.md` — Bot wiring, /status command, publish_queue
- `.planning/phases/02-ai-handler/02-CONTEXT.md` — AIConsumer pattern, AllModelsExhausted, backpressure, TokenBucket
- `.planning/phases/01-configuration-crawler/01-CONTEXT.md` — Backoff constants, source pause logic

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/logging_setup.py` — `RotatingFileHandler`, `setup_logging()`. Modify for config-driven levels and increased retention.
- `src/ai_handler.py` `AIConsumer.shutdown()` — `asyncio.Event` pattern directly reusable for cooldown timer pause mechanism.
- `src/ai_handler.py` `TokenBucket` — Rate limiter pattern, can be adapted for per-event-type alert cooldowns.
- `src/bot_reviewer.py` `startup_notification()` — Existing `send_message` pattern for alerts.
- `src/bot_reviewer.py` `/status` command — Extend with health info and metrics.
- `src/crawler.py` — Backoff constants defined at module level, currently used inline.

### Established Patterns
- `asyncio.Event` for shutdown signaling (all consumers)
- Queue consumer pattern: producer → `asyncio.Queue` → consumer (all phases)
- Backpressure logging via `qsize()` warnings (all consumers)
- Module-per-responsibility in `src/` with Pydantic models
- `logger.exception()` in all `except` blocks
- httpx.AsyncClient injected from `main.py`, not created per-module

### Integration Points
- `src/main.py` — Must create `HealthCollector`, register all module callbacks, pass to bot
- `src/bot_reviewer.py` — Register `/health` command handler alongside `/status`
- `src/ai_handler.py` — Add cooldown Event that workers check; register health callback with `HealthCollector`
- `src/crawler.py` — Add disconnect detection and reconnection health reporting
- `src/logging_setup.py` — Modify to support config-driven log levels per module
- `src/config.py` — Add `LOG_LEVELS` config key
- All modules — Add structured error code logging; add health callback for `/health`

</code_context>

<specifics>
## Specific Ideas

- Error code prefix pattern: `[ERR_CODE]` in log messages for grep-ability
- HealthCollector as a registry: modules call `health.register("crawler", check_fn)` at init
- `/health` response format should be easy to parse visually and via grep
- Daily metrics file written at shutdown or via a periodic timer (every N minutes flush aggregated counters)
- DLQ can use a simple counter/message-id list exposed via /health rather than full message persistence

</specifics>

<deferred>
## Deferred Ideas

- JSON logging for log aggregation pipeline — no consumer yet
- Queue depth time-series metrics file — snapshot to log is sufficient for v1
- Per-event metrics append (granular logging per publish) — per-day aggregate is sufficient for v1
- Auto-retry with exponential backoff for failed platforms — deferred from Phase 4 D-04, still deferred
- Alert routing via external services (PagerDuty, email) — Telegram alerts are sufficient for v1
- Persistent DLQ (database-backed) — in-memory is sufficient for v1

</deferred>

---

*Phase: 05-resilience-logging-monitoring*
*Context gathered: 2026-05-17*
