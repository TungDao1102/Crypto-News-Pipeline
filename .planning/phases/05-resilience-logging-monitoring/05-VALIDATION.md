---
phase: 05
slug: resilience-logging-monitoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-17
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — use project defaults |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_health.py tests/test_queue_utils.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | HEALTH-01 | T-05-01 | Health output excludes secrets | unit | `pytest tests/test_health.py::test_collector_runs_all_checks -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | HEALTH-02 | T-05-01 | Timeout isolates unresponsive callback | unit | `pytest tests/test_health.py::test_check_timeout -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | HEALTH-03 | T-05-04 | Cooldown suppresses duplicates within 30 min window | unit | `pytest tests/test_health.py::test_alert_cooldown -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | HEALTH-08 | T-05-04 | Queue depth >50 triggers mode switch + alert | integration | `pytest tests/test_health.py::test_queue_depth_alert -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | HEALTH-04 | T-05-03 | BoundedQueue drops oldest when full | unit | `pytest tests/test_queue_utils.py::test_bounded_queue_eviction -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 1 | HEALTH-05 | — | AIConsumer pause Event stops workers, auto-resumes | integration | `pytest tests/test_ai_handler.py::test_pause_cooldown -x` | ❌ W0 | ⬜ pending |
| 05-04-01 | 04 | 1 | HEALTH-06 | T-05-02 | Per-module log levels applied correctly | unit | `pytest tests/test_logging_setup.py::test_module_levels -x` | ❌ W0 | ⬜ pending |
| 05-05-01 | 05 | 1 | HEALTH-07 | T-05-03 | Daily metrics file written on shutdown | integration | `pytest tests/test_metrics.py::test_flush_on_shutdown -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_health.py` — stubs for HEALTH-01, HEALTH-02, HEALTH-03, HEALTH-08
- [ ] `tests/test_queue_utils.py` — stubs for HEALTH-04
- [ ] `tests/test_ai_handler.py` — add `test_pause_cooldown` for HEALTH-05
- [ ] `tests/test_logging_setup.py` — stubs for HEALTH-06
- [ ] `tests/test_metrics.py` — stubs for HEALTH-07
- [ ] `tests/conftest.py` — shared fixtures (mock PTB bot, HealthCollector with wired bot)
- [ ] `pip install pytest pytest-asyncio` — if not detected

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin receives /health reply via Telegram bot | HEALTH-01 | Requires live Telegram bot | Run bot, send /health, confirm reply includes per-module status |
| Alert sent on publisher permanent error | HEALTH-08 | Requires live Binance API or mock | Simulate ban error code in publisher, confirm alert arrives via bot DM |
| Daily metrics file written to logs/metrics/ | HEALTH-07 | File system write | Run pipeline for 1+ day (or simulate shutdown), confirm `logs/metrics/YYYY-MM-DD.json` exists with valid JSON |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
