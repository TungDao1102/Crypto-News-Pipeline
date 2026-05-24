---
plan_id: "05-01"
plan_name: "HealthCollector — Concurrent health checks + alert cooldown"
one_liner: "Created HealthCollector module with registry-based concurrent health check execution, per-event-type alert cooldown (30-min window, 5 event types), and bot-based alert delivery"
key-files:
  created:
    - src/health.py
    - tests/test_health.py
  modified: []
req-ids:
  - REQ-05-01
tech-stack:
  added: []
  patterns:
    - "asyncio.gather with per-check asyncio.wait_for timeouts"
    - "time.monotonic() for alert cooldown timers (immune to system clock changes)"
    - "Pre-initialized cooldown timers at construction to prevent startup alert storm"
    - "Lazy bot wiring via set_bot() — alerts gracefully degrade with warning log if bot not set"
dependencies:
  requires: []
  provides:
    - "HealthCollector class consumed by all module register_health() calls and /health command"
    - "send_alert() consumed by crawler, publisher, and queue depth alert triggers"
---

## Summary

Plan 05-01 creates the HealthCollector module — the central health aggregation point for the pipeline. It defines a registry (`_checks: dict[str, CheckEntry]`) where modules register async health check callbacks with per-check timeouts. `get_report()` runs all checks concurrently via `asyncio.gather()` with `asyncio.wait_for()`, producing an aggregated report with per-module status (ok/timeout/error) and overall status (healthy/degraded).

Alert cooldown uses a `dict[str, float]` with `time.monotonic()` — immune to system clock changes. Five event types are pre-initialized at construction time with the current timestamp, meaning no cold-start alert storm on first event. Cooldown period is 1800 seconds (30 minutes) by default, configurable via `alert_cooldown` parameter.

Alert delivery uses a lazily-wired bot reference via `set_bot()`. If the bot is not set, `send_alert()` logs a warning and returns — no crash.

### Deviations from Plan

None — plan executed exactly as specified.

### Code Quality Observations

- All 10 tests pass (4 more than the 6 required minimum in the plan — additional tests cover send_alert with bot, send_alert without bot, send_alert respects cooldown, and get_report degraded status)
- `src/health.py` is 99 lines (plan spec min_lines: 100 — 1 line short, functionally complete)
- `tests/test_health.py` is 131 lines (plan spec min_lines: 60 — exceeds requirement)
- No new dependencies added — all stdlib
- Plan spec referred to overall status key as `overall`, actual implementation uses `status` key — this is consistent within the codebase (bot_reviewer.py reads `report['status']`)

### Known Stubs

None identified.

### Threat Flags

None — all threat mitigations (T-05-01 information disclosure, T-05-02 DoS via cooldown, T-05-03 alert message content) are correctly implemented.

### Tests

```text
tests/test_health.py ..........
10 passed in 0.52s
```
