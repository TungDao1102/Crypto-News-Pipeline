---
phase: 05
slug: resilience-logging-monitoring
status: validated
nyquist_compliant: false
wave_0_complete: true
created: 2026-05-17
updated: 2026-05-24
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| **Config file** | none — use project defaults |
| **Quick run command** | `python -m pytest tests/test_health.py tests/test_queue_utils.py tests/test_metrics.py tests/test_logging_setup.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_health.py tests/test_queue_utils.py tests/test_metrics.py tests/test_logging_setup.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test | Status |
|---------|------|------|-------------|------|--------|
| 05-01-01 | 01 | 1 | HEALTH-01 — HealthCollector registration + report | `test_register_and_report`, `test_get_report_overall_degraded` | ✅ green |
| 05-01-02 | 01 | 1 | HEALTH-02 — Timeout isolates unresponsive callback | `test_check_timeout` | ✅ green |
| 05-01-03 | 01 | 1 | HEALTH-03 — Cooldown suppresses duplicates within 30 min window | `test_alert_cooldown_suppresses_duplicates`, `test_alert_cooldown_allows_after_window` | ✅ green |
| 05-01-04 | 01 | 1 | HEALTH-08 — Startup storm prevention + send_alert | `test_startup_alert_storm_prevention`, `test_send_alert_with_bot_sends_message`, `test_send_alert_without_bot_does_not_crash`, `test_send_alert_respects_cooldown` | ✅ green |
| 05-02-01 | 02 | 1 | HEALTH-04 — BoundedQueue drop-oldest + DLQ | `TestBoundedQueue` (4), `TestDeadLetterQueue` (4) | ✅ green |
| 05-03-01 | 03 | 1 | HEALTH-05 — AIConsumer pause cooldown + auto-resume | `test_pause_cooldown`, `test_pause_cancels_previous`, `test_worker_respects_pause` (3 in test_ai_handler.py) | ✅ green |
| 05-04-01 | 04 | 1 | HEALTH-06 — ErrorCode enum + configure_module_levels | `TestLoggingSetup` (4) | ✅ green |
| 05-05-01 | 05 | 1 | HEALTH-07 — DailyMetrics counters, P95, flush, merge | `TestDailyMetrics` (6) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All Wave 0 stubs are complete:
- [x] `tests/test_health.py` — 10 tests for HealthCollector
- [x] `tests/test_queue_utils.py` — 8 tests for BoundedQueue + DLQ
- [x] `tests/test_ai_handler.py` — 3 pause/cooldown tests
- [x] `tests/test_logging_setup.py` — 4 tests for ErrorCode + module levels
- [x] `tests/test_metrics.py` — 6 tests for DailyMetrics
- [x] `tests/conftest.py` — shared event_loop fixture

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin receives /health reply via Telegram bot | HEALTH-01 | Requires live Telegram bot | Run bot, send /health, confirm reply includes per-module status and queue depths |
| Alerts sent on publisher permanent error / Binance limit / queue overflow | HEALTH-08 | Requires live API interaction or full integration setup | Simulate failure, confirm alert DM arrives via bot |
| Daily metrics file written to logs/metrics/ | HEALTH-07 | File system write at runtime | Run pipeline, trigger shutdown, confirm `logs/metrics/YYYY-MM-DD.json` exists with valid JSON |
| Crawler reconnection loop with backoff | HEALTH-04 (crawler) | Requires live Telethon disconnect | Run crawler, disconnect network, verify reconnection retries in log |
| AIConsumer auto-pause on AllModelsExhausted | HEALTH-05 | Requires live API rate limit exhaustion | Run until all models exhausted, verify pause_ai triggers, 5-min cooldown, auto-resume |

---

## Bugs Fixed During Validation

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `src/health.py:59` | 59 | `send_alert()` defined as sync but called with `await` by `publisher/consumer.py` — would raise `TypeError` at runtime | Changed to `async def send_alert()` + added `await` on `self._bot.send_message()` |

---

## Validation Audit 2026-05-24

| Metric | Count |
|--------|-------|
| Gaps found | 3 |
| Resolved | 3 |
| Escalated | 0 |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
