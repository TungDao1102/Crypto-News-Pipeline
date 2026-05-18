---
plan_id: "05"
plan_name: "Resilience, Logging & Monitoring"
one_liner: "Add health introspection, memory protection, failure isolation, operational metrics, structured error codes, admin alerting, and auto-pause for AI model exhaustion."
key-files:
  created:
    - src/health.py
    - src/queue_utils.py
    - src/metrics.py
    - tests/test_health.py
    - tests/test_queue_utils.py
    - tests/test_metrics.py
    - tests/test_logging_setup.py
    - tests/conftest.py
  modified:
    - src/ai_handler.py
    - src/logging_setup.py
    - src/config.py
    - src/main.py
    - src/bot_reviewer.py
    - src/crawler.py
    - src/publisher/consumer.py
    - src/publisher/telegram.py
    - src/publisher/binance_square.py
    - src/system_state.py
req-ids:
  - REQ-05-01 (HealthCollector + alert cooldown)
  - REQ-05-02 (BoundedQueue + DeadLetterQueue)
  - REQ-05-03 (DailyMetrics collector)
  - REQ-05-04 (ErrorCode enum, log retention, module log levels)
  - REQ-05-05 (AIConsumer pause cooldown)
  - REQ-05-06 (Wiring: health callbacks, /health command, alerts, error codes, metrics wiring)
---

## Summary

Phase 5 implements the resilience, logging, and monitoring layer for the Crypto News & Airdrop Automation Pipeline. It introduces a HealthCollector with per-event-type alert cooldown (30-min window, 5 event types), BoundedQueue (200-item drop-oldest) and DeadLetterQueue for memory protection and failure isolation, DailyMetrics counters with P95 latency tracking and merge-on-write file flush, a structured ErrorCode enum (10 codes) with ec() formatting helper, config-driven per-module log levels, 50MB×10 log retention, an AIConsumer auto-pause mechanism on AllModelsExhausted with 5-min cooldown, and comprehensive wiring including /health command, reconnection loop with backoff, alert triggers for queue overflow/source disconnect/Binance limit/publisher errors, approve/reject metric tracking, and periodic queue depth logging.
