---
plan_id: "05-04"
plan_name: "Logging Upgrade — ErrorCode enum, retention, per-module log levels"
one_liner: "Added structured ErrorCode enum (10 codes) with ec() helper, increased log retention to 50MB x 10 backups, config-driven per-module log levels via LOG_LEVELS env var, and shared test conftest"
key-files:
  created:
    - tests/test_logging_setup.py
    - tests/conftest.py
  modified:
    - src/logging_setup.py
    - src/config.py
    - src/main.py
req-ids:
  - REQ-05-04
tech-stack:
  added:
    - "enum.Enum (stdlib, already available)"
  patterns:
    - "ErrorCode(str, Enum) — enum values are human-readable error code strings"
    - "ec(code, message) → f'[{code.value}] {message}' — lightweight formatting, not a custom log adapter"
    - "LogLevelsConfig type alias for type-safe per-module level configuration"
    - "configure_module_levels() validates levels via getattr(logging, level_name.upper())"
dependencies:
  requires: []
  provides:
    - "ErrorCode enum used by all modules for structured error logging"
    - "configure_module_levels() called in main.py after setup_logging()"
    - "Config.log_levels loaded from LOG_LEVELS env var (optional, defaults None)"
---

## Summary

Plan 05-04 upgrades the logging infrastructure with three improvements:

**1. ErrorCode enum (10 codes) + ec() helper** — Added to `src/logging_setup.py`. Covers all alert event types plus operational codes: QUEUE_OVERFLOW, ALL_MODELS_EXHAUSTED, PUBLISH_FAIL, SOURCE_DISCONNECT, JSON_VALIDATION_FAIL, BINANCE_DAILY_LIMIT, BOT_PERMISSION, DLQ_ITEM_ADDED, QUEUE_DEPTH_CRITICAL, MODE_AUTO_SWITCH. The `ec()` function returns a plain string compatible with existing `logger.info/warning/error/exception()` calls.

**2. Retention increase (50MB x 10)** — RotatingFileHandler changed from 10MB x 5 backups to 50MB x 10 backups for more debug history.

**3. Per-module log levels** — `configure_module_levels()` function accepts a `dict[str, str]` mapping logger names to level strings. The `Config` class gains `log_levels` attribute loaded from the `LOG_LEVELS` environment variable (optional JSON dict). `main.py` calls `configure_module_levels(config.log_levels)` after `setup_logging()`. Invalid levels log a warning without crashing; None input returns silently.

**4. Test infrastructure** — `tests/test_logging_setup.py` (4 tests) and `tests/conftest.py` (event_loop fixture for async tests) created.

### Deviations from Plan

None — plan executed exactly as specified.

### Code Quality Observations

- All 4 tests pass
- `src/logging_setup.py` is 68 lines — compact and focused
- LOG_LEVELS env var parsing includes JSON decode validation and type check (`isinstance(dict)`) — invalid input is ignored with warning (per T-05-08 mitigation)
- `src/config.py` correctly keeps LOG_LEVELS optional — not added to REQUIRED_KEYS

### Known Stubs

None identified.

### Threat Flags

None — T-05-08 (LOG_LEVELS JSON validation) and T-05-09 (ErrorCode descriptive strings) are correctly implemented.

### Tests

```text
tests/test_logging_setup.py ....
4 passed in 0.28s
```
