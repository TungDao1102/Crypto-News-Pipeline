# Phase 5: Resilience, Logging & Monitoring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 05-resilience-logging-monitoring
**Areas discussed:** Alert delivery, Queue auto-mitigation, Logging format & levels, Metrics tracking

---

## Alert Delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Telegram bot DM | Reuse PTB send_message to ADMIN_CHAT_ID | |
| Both DM + /health cmd | Push alerts + on-demand status command | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Source disconnect | Telethon drops after max retries | ✓ |
| Queue depth critical | >50 items | ✓ |
| Binance daily limit | Error code 220009 | ✓ |
| Publisher permanent error | Account ban, bot removed from channel | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| First-only + cooldown | Fire once per event, suppress 30 min | ✓ |
| Rate-limited | Max 1 per 5 min | |
| Aggregate summary | Batch events over window | |

| Option | Description | Selected |
|--------|-------------|----------|
| Simple text | Mode + queue depths + processed count | |
| Per-module + timestamps | Each module reports own status + last activity | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| All models exhausted → pause | AI-SPEC §6.2 | ✓ |
| All models + source disconnect → pause | Broader auto-pause | |
| Only all models → pause | Keep modules independent | |

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone health module | src/health.py with HealthCollector | ✓ |
| Inline in SystemState | Simpler but less clean | |

**User's choice:** Both alert channels, 4 alert triggers, first-only + 30min cooldown, per-module /health, pause on all-models-exhausted only, standalone HealthCollector
**Notes:** Alerts are fire-and-forget push. /health gives on-demand introspection. Source disconnect doesn't pause AI because queued messages should still be processable.

---

## Queue Auto-Mitigation

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-switch | Bot auto-switches to MANUAL, admin must revert | ✓ |
| Admin-confirmed | Send Approve/Reject inline keyboard | |

| Option | Description | Selected |
|--------|-------------|----------|
| Buffer in memory | Keep queuing indefinitely | |
| Drop oldest when >200 | Hard cap per queue | ✓ |
| Log warning + persist | Log CRITICAL, keep buffering | |

| Option | Description | Selected |
|--------|-------------|----------|
| No DLQ in v1 | Log + skip, matches prior phases | |
| Simple DLQ | In-memory DLQ, inspectable via /health | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| asyncio Event + cooldown timer | Workers check before processing | ✓ |
| Rate limiter pause | Set refill_rate to 0 | |

**User's choice:** Auto-switch to MANUAL, drop oldest when >200 per queue, simple in-memory DLQ, asyncio Event cooldown
**Notes:** DLQ is simple in-memory — admin can inspect via /health. Hard cap prevents unbounded memory growth during sustained overload.

---

## Logging Format & Levels

| Option | Description | Selected |
|--------|-------------|----------|
| Keep human-readable only | Current format | ✓ |
| Add JSON file handler | Dual logging | |

| Option | Description | Selected |
|--------|-------------|----------|
| Config-driven levels | LOG_LEVELS config per module | ✓ |
| Single global level | One LOG_LEVEL for everything | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — prefix codes | [ERR_CODE] pattern | ✓ |
| No — descriptive messages | Current approach | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current | 10MB × 5 | |
| Increase retention | 50MB × 10 | ✓ |
| Add daily rotation | Rotate by date | |

**User's choice:** Human-readable only, config-driven per-module levels, structured error codes [ERR_CODE], 50MB × 10 backups
**Notes:** JSON logging adds complexity with no consumer. Error codes enable grep-based filtering without needing structured logging.

---

## Metrics Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| Approve/reject ratio | Daily aggregate | ✓ |
| JSON validation errors | Per-day count | ✓ |
| API latency P95 | Hourly metric | ✓ |
| Queue depth time-series | Every 5 min | |

| Option | Description | Selected |
|--------|-------------|----------|
| Daily metrics file | logs/metrics/YYYY-MM-DD.json | |
| Extended /status command | Add to existing bot command | |
| Both | File + /status | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory + max only | Track max queue depth in SystemState | |
| Snapshot to log file | Log at intervals | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Per-day aggregate | End-of-day rollup | ✓ |
| Per-event append | JSON line per event | |

**User's choice:** 3 v1 metrics (skip queue depth time-series), both daily file + /status, queue depth to log, per-day aggregate
**Notes:** Queue depth time-series deferred — snapshot to log is sufficient for v1. Daily metrics file written at end-of-day or on shutdown.

---

## the agent's Discretion

- Exact error code strings and code list
- `/health` response format details
- Metrics file schema (exact JSON structure)
- Which events to log at which level for structured codes
- DLQ admin retry mechanism implementation
- Health check callback interface (how modules register)
- Queue hard cap constants (200 vs other value if testing shows different)
- Cooldown timer duration for alerts (30 min default, fine-tune later)
- Cooldown timer location (HealthCollector vs per-module)

## Deferred Ideas

- JSON logging for log aggregation pipeline
- Queue depth time-series metrics file
- Per-event metrics append (granular logging per publish)
- Auto-retry with exponential backoff for failed platforms (deferred from Phase 4)
- Alert routing via external services (PagerDuty, email)
- Persistent DLQ (database-backed)
