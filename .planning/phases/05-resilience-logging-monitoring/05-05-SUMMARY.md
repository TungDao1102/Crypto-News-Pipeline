---
plan_id: "05-05"
plan_name: "AIConsumer Auto-Pause — AllModelsExhausted cooldown with 5-min auto-resume"
one_liner: "Added asyncio.Event-based pause mechanism to AIConsumer with 5-minute cooldown on AllModelsExhausted, auto-resume via background task, and worker loop pause check"
key-files:
  created: []
  modified:
    - src/ai_handler.py
    - tests/test_ai_handler.py
req-ids:
  - REQ-05-05
tech-stack:
  added: []
  patterns:
    - "asyncio.Event for pause signaling (independent of shutdown Event)"
    - "Cooldown timer runs as background asyncio.Task — does not block event loop"
    - "Worker loop checks _pause.is_set() before processing, sleeps 1s and retries"
    - "Previous cooldown is cancelled on new pause_ai() call (restarts timer)"
    - "ErrorCode.ALL_MODELS_EXHAUSTED used in log messages for structured tracing"
dependencies:
  requires:
    - "05-04 (ErrorCode enum from logging_setup.py)"
  provides:
    - "_pause Event, _pause_until timestamp for health check reporting (Plan 06)"
    - "Pause triggered in _process_message AllModelsExhausted exception handlers"
---

## Summary

Plan 05-05 adds an auto-pause mechanism to the AIConsumer class:

- **`_pause` Event** — Independent asyncio.Event orthogonal to `_shutdown`. Set = paused, clear = running.
- **`pause_ai(duration=300)`** — Sets `_pause`, records `_pause_until` timestamp, cancels any existing cooldown task, creates new `_auto_resume` background task.
- **`_auto_resume(duration)`** — Sleeps for duration, then clears `_pause` and resets `_pause_until`.
- **Worker loop** — Checks `_pause.is_set()` before processing a message; if paused, sleeps 1 second and retries.
- **`_last_processed_time`** — ISO timestamp updated after each successful message processing.

The AllModelsExhausted exception handlers in `_process_message()` (both translate and rewrite paths) now call `await self.pause_ai()` before returning. The translate exhaustion path returns None (draft skipped). The rewrite exhaustion path returns a fallback DraftContent using translated text.

### Deviations from Plan

None — plan executed exactly as specified. Tests are embedded in the existing `tests/test_ai_handler.py` file alongside pre-existing tests.

### Code Quality Observations

- All 3 pause-specific tests pass (test_pause_cooldown, test_pause_cancels_previous, test_worker_respects_pause — in both TestAIConsumer class and standalone integration test form)
- `_process_message` already existed in the codebase — Plan 05 only modified the exception handlers (adds `await self.pause_ai()` + structured error code logging)
- Worker loop is inside `_worker()` method — shutdown check comes first, pause check immediately follows
- The `_pause_until` timestamp enables `_cooldown_remaining()` for health check reporting (wired in Plan 06)

### Known Stubs

None identified.

### Threat Flags

None — T-05-10 (cooldown timer cancellation safety) and T-05-11 (spurious pause only triggered by AllModelsExhausted) are correctly implemented.

### Tests

```text
tests/test_ai_handler.py ... (3 pause-specific tests pass, included in total 53)
```
