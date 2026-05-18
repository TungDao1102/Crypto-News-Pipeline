---
plan_id: "04"
plan_name: "Publisher & Platform Integration"
one_liner: "Consume approved DraftContent from publish queue, inject platform formatting (cashtags/hashtags), publish to Telegram Channel and Binance Square, track per-platform results, and set status to published on any success."
key-files:
  created:
    - src/publisher/__init__.py
    - src/publisher/base.py
    - src/publisher/tag_injector.py
    - src/publisher/telegram.py
    - src/publisher/binance_square.py
    - src/publisher/consumer.py
  modified:
    - src/models.py
    - src/bot_reviewer.py
    - src/main.py
req-ids:
  - REQ-04-01 (BasePublisher + PublishResult)
  - REQ-04-02 (TagInjector — cashtag/hashtag injection)
  - REQ-04-03 (Telegram + Binance Square platform publishers)
  - REQ-04-04 (PublisherConsumer with dedup + 2s cooldown)
  - REQ-04-05 (Wiring: run_bot signature + main.py lifecycle)
---

## Summary

Phase 4 implements the publisher pipeline for the Crypto News & Airdrop Automation Pipeline. It consumes approved `DraftContent` from the publish queue, injects platform-required cashtag/hashtag formatting, and publishes to Telegram Channel (via existing PTB Bot API with HTML parse_mode) and Binance Square (via OpenAPI with Markdown stripping). Each publish generates a structured `PublishResult`, and the draft status transitions to `"published"` when at least one platform succeeds. A 2-second cooldown is enforced between platform publishes, and an in-memory dedup set prevents double-publishing.
