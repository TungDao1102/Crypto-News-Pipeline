# Publisher & Platform Integration — Phase 4 Plan

## Goal
Consume approved `DraftContent` objects from the publish queue, inject platform-required formatting (cashtags, hashtags), publish to Telegram Channel (via existing PTB Bot API) and Binance Square (via OpenAPI), track per-platform publish results, set draft status to `"published"` when at least one platform succeeds, and enforce a 2-second cooldown between publishes.

## Task Breakdown

### Wave 1: Foundation
Implement base classes, publisher interface, PublishResult model, and shared tag injector.

| Plan | Task | Description |
|------|------|-------------|
| P-01 | Base publisher + PublishResult model | Create `src/publisher/base.py` with `PublisherResult` dataclass and abstract `BasePublisher` class (`publish` method, `close` method). Add `PublishResult` to `src/models.py` with `platform: Literal["telegram", "binance_square"]`, `success: bool`, `url: str \| None`, `error: str \| None`. |
| P-02 | Tag injector utility | Create `src/publisher/tag_injector.py` with `TagInjector` class that strips pre-existing tags, injects a block of `#Tag` and `$TICKER` tags capped at 3 cashtags (from priority list: BTC, ETH, SOL, ARB, OP, MATIC, AVAX, ATOM) and 5 hashtags (mapped from content tags: airdrop, testnet, retroactive, defi, nft, gamefi, layer2, staking), respecting 4096-char limit. |

### Wave 2: Platform Publishers

| Plan | Task | Description |
|------|------|-------------|
| P-03 | Telegram + Binance Square publishers | Create `src/publisher/telegram.py` with `TelegramPublisher(BasePublisher)` using PTB's `application.bot.send_message()` with `parse_mode=ParseMode.HTML`. Create `src/publisher/binance_square.py` with `BinanceSquareClient` (replicating `OpenRouterClient` pattern from `ai_handler.py`) and `BinanceSquarePublisher(BasePublisher)`. **Markdown stripping**: convert `**bold**` → `bold`, `*italic*` → `italic`, `[text](url)` → `text (url)`, strip `#` prefixes from headings before publishing. Include `clienttype: binanceSkill` header. Classify error code 220009 (daily limit) as warning, don't retry. |

### Wave 3: Integration

| Plan | Task | Description |
|------|------|-------------|
| P-04 | Publisher consumer + deduplication | Create `src/publisher/consumer.py` with `PublisherConsumer` (replicating `AIConsumer` queue-consumer pattern) that pops from `publish_queue`, injects tags via TagInjector, publishes to each platform sequentially (2s cooldown per D-06), updates `DraftContent.status = "published"` on any success, and logs `PublishResult`. Include in-memory `set[str]` of published draft IDs to prevent double-publishing. |
| P-05 | Wiring + parameter passing | Update `bot_reviewer.py` `run_bot()` to accept `http_client: httpx.AsyncClient` and `binance_api_key: str` parameters. Create `PublisherConsumer` inside `run_bot()` (has access to `application.bot`). Pass `http_client` and `binance_api_key` from `main.py`. Register `publisher_consumer.shutdown()` in bot's finally block. Add `publisher_consumer.start()` to `asyncio.gather` in `main.py`. |

## Wave Sequencing & Dependencies
- **Wave 1** must complete before **Wave 2** (base class + model needed by platform publishers).
- **Wave 1 + Wave 2** must complete before **Wave 3** (publisher consumer needs platform publishers and tag injector).
- **Wave 3 P-05** depends on P-04 (consumer must exist before wiring).

## Success Criteria
1. Approved `DraftContent` from `publish_queue` is published to Telegram Channel (HTML format, with cashtags/hashtags injected).
2. Approved `DraftContent` from `publish_queue` is published to Binance Square (plain text, Markdown stripped, max 3 cashtags).
3. Both platforms publish independently — if one fails, the other still succeeds (D-04).
4. Each publish generates a `PublishResult` with platform, url, post_id, success/error status.
5. `DraftContent.status` transitions from `"approved"` to `"published"` after successful publish to at least one platform.
6. 2-second cooldown enforced between platform publishes (D-06).
7. Double-publishing prevented via in-memory dedup set (D-03).

## AI-SPEC Conflicts Resolution
- **§7.4 lists 8 priority coins → Cap at 3 cashtags** (RESEARCH.md finding: Binance Square max 3 cashtags per post). Injector selects top 3 matching the content's tags from the priority list.
- **§7.3 specifies Telegram `parse_mode="MarkdownV2"` → Use `parse_mode="HTML"`** (RESEARCH.md finding: HTML only needs 3 chars escaped vs MarkdownV2's 7+). Safer for AI-generated content.
- **§4.2 `publisher.py` module → Use `src/publisher/` package** (PATTERNS.md recommendation for cleaner separation across 5+ classes).

## Code Quality
- Type hints on all function signatures and class attributes.
- All publisher classes must satisfy `mypy --strict` (no `Any`, no implicit `Optional`).
- All error handling follows D-04: log error, continue to next platform.
- Rate limiting via simple `asyncio.sleep(2.0)` after each publish cycle.
- Tag injector must never produce output exceeding Telegram 4096-char or Binance Square's ~4000-char limit.
- Tag injector must strip any pre-existing tags from content before injecting deterministic ones (D-03).
- Binance Square API calls must include `clienttype: binanceSkill` header alongside `X-Square-OpenAPI-Key` (RESEARCH.md finding #2).
- Error code 220009 (daily limit) must be caught and logged as warning, not retried (RESEARCH.md finding #4).
