---
phase: 04
slug: publisher
status: validated
nyquist_compliant: false
created: 2026-05-24
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| **Config file** | none — tests run from project root |
| **Quick run command** | `python -m pytest tests/test_publisher.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_publisher.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test | Status |
|---------|------|------|-------------|------|--------|
| 04-01 | P-01 | 1 | REQ-04-01 — BasePublisher + PublisherResult + PublishResult | `TestPublisherResultDataclass` (2), `TestBasePublisher` (3), `TestPublishResultPydanticModel` (4) | ✅ green |
| 04-02 | P-02 | 1 | REQ-04-02 — TagInjector (strip, select cashtags, select hashtags, inject) | `TestTagInjectorStripTags` (4), `TestTagInjectorSelectCashtags` (5), `TestTagInjectorSelectHashtags` (5), `TestTagInjectorInject` (5) | ✅ green |
| 04-03 | P-03 | 2 | REQ-04-03 — TelegramPublisher + BinanceSquarePublisher + strip_markdown | `TestStripMarkdown` (7), `TestBinanceSquareClient` (3), `TestBinanceSquarePublisher` (7), `TestTelegramPublisher` (6) | ✅ green |
| 04-04 | P-04 | 3 | REQ-04-04 — PublisherConsumer dedup + cooldown + status transition | `TestPublisherConsumerHealth` (4) | ✅ green |
| 04-05 | P-05 | 3 | REQ-04-05 — Wiring: run_bot signature + main.py lifecycle | Indirect via consumer creation test | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PublisherConsumer start() actually processes queue items in real asyncio loop | 04-04 — REQ-04-04 | Requires live asyncio event loop with real queue interaction | Run with approved draft in queue: `python src/main.py`, verify "Draft published" log |
| Telegram publish to real channel | 04-03 — REQ-04-03 | Requires live Telegram bot + channel | Publish approved draft, verify message appears in Telegram channel |
| Binance Square publish to real platform | 04-03 — REQ-04-03 | Requires live Binance Square API key | Publish approved draft, verify post appears on Binance Square |
| run_bot wiring with PublisherConsumer lifecycle (shutdown on cancel) | 04-05 — REQ-04-05 | Integration test, requires full application wiring | Start `python src/main.py`, Ctrl+C, verify clean shutdown log |
| Binance Square 220009 daily limit recovery | 04-03 — REQ-04-03 | Requires real API key hitting daily limit | Run until limit hit, verify WARNING log, no retry, health alert sent |

---

## Bugs Fixed During Validation

The following implementation bug was discovered and fixed:

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `src/publisher/base.py:11` | 11 | `PublisherResult` dataclass missing `post_id` field | Added `post_id: str \| None = None` |

The `binance_square.py:90` code passes `post_id=str(post_id)` to `PublisherResult`, but the dataclass lacked this field, causing a `TypeError` at runtime. The Pydantic `PublishResult` model in `src/models.py` already had the field correctly.

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none needed)
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
