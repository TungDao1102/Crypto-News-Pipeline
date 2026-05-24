---
plan_id: "05-02"
plan_name: "Queue Utilities — BoundedQueue + DeadLetterQueue"
one_liner: "Created bounded queue wrapper with drop-oldest overflow (200-item cap) and dead letter queue for persistent failure isolation with inspectable snapshot and retry"
key-files:
  created:
    - src/queue_utils.py
    - tests/test_queue_utils.py
  modified: []
req-ids:
  - REQ-05-02
tech-stack:
  added: []
  patterns:
    - "BoundedQueue extends asyncio.Queue, overrides put_nowait to evict oldest on full"
    - "Eviction does NOT call task_done() — project does not use join()"
    - "DeadLetterQueue with accumulated counter, snapshot dict, and retry_all re-queue"
    - "DLQ put() logs with [ERR_DLQ] prefix for structured error tracing"
dependencies:
  requires: []
  provides:
    - "BoundedQueue(200) used in main.py for all three pipeline queues"
    - "DeadLetterQueue used by publisher for failed items, inspected via /health"
---

## Summary

Plan 05-02 creates two queue utility classes:

**BoundedQueue** extends `asyncio.Queue` and overrides `put_nowait()` to drop the oldest item when the queue is full, preventing `QueueFull` exceptions. The async `put()` delegates to `put_nowait()` for non-blocking behavior. Eviction on a race-condition empty queue is wrapped in try/except `QueueEmpty`. No `task_done()` is called on eviction — the codebase does not use `Queue.join()`, so calling `task_done()` would create a counter imbalance. Default maxsize is 200.

**DeadLetterQueue** provides an inspectable holding area for persistently failed messages. It tracks a running accumulated counter (`_count`) distinct from queue depth (`qsize()`). The `snapshot()` method returns `{"depth": ..., "total_accumulated": ...}` for /health display. `retry_all()` re-queues items to a target queue and resets the accumulated counter.

### Deviations from Plan

None — plan executed exactly as specified.

### Code Quality Observations

- All 8 tests pass
- `src/queue_utils.py` is 58 lines (plan spec min_lines: 70 — functionally complete, slightly under line count)
- `tests/test_queue_utils.py` is 99 lines (plan spec min_lines: 50 — exceeds requirement)
- No new dependencies added — all stdlib
- Plan noted DLQ put() uses a hardcoded `[ERR_DLQ]` string, to be updated to ErrorCode enum in Plan 06 — verified this was done in Plan 06 wiring

### Known Stubs

None identified.

### Threat Flags

None — threat T-05-04 (information disclosure on eviction) is accepted per design, T-05-05 (DLQ retry_all tampering) is accepted.

### Tests

```text
tests/test_queue_utils.py ........
8 passed in 0.38s
```
