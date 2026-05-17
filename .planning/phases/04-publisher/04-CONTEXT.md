# Phase 4: Publisher & Platform Integration - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Consume approved `DraftContent` objects from the publish queue, inject platform-required formatting (cashtags, hashtags), publish simultaneously to Telegram Channel (via Bot API) and Binance Square (via OpenAPI), track per-platform publish results, and set draft status to `"published"` when at least one platform succeeds.

</domain>

<decisions>
## Implementation Decisions

### Telegram Publish Method
- **D-01:** Reuse existing `python-telegram-bot` (PTB) `application.bot.send_message()` to publish to `TELEGRAM_CHANNEL_ID`. No new connection or dependency. The bot must be added as admin to the target Telegram channel.

### Binance Square Integration
- **D-02:** Direct `httpx` POST to `https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add`. Header `X-Square-OpenAPI-Key: {api_key}`. Body `{"bodyTextOnly": "content"}`. Text-only posts — no media support in v1.

### Cashtag / Hashtag Injection
- **D-03:** Last-minute injector pattern — strip any existing tags from AI output, inject deterministically based on `DraftContent.tags` field + coin-to-cashtag mapping list. Clean separation: AI writes content, injector handles platform formatting compliance.

### Partial Failure Handling
- **D-04:** Continue on partial failure. Publish to whatever platform succeeds. Log failures with structured error info. Set `DraftContent.status = "published"` if at least one platform succeeds. No retry for failed platforms in v1.

### PublishResult Model
- **D-05:** Per-platform results — `list[PublishResult]` where each has:
  - `platform: Literal["telegram", "binance_square"]`
  - `success: bool`
  - `url: str | None` — post URL (constructable for Binance Square from returned `data.id`)
  - `error: str | None`

### Rate Limiting
- **D-06:** Simple 2-second cooldown between each draft's platform publishes (Telegram + Binance Square). No TokenBucket needed — consistent cooldown is sufficient to stay under both API rate limits.

### the agent's Discretion
- Exact retry count for individual API call errors (connection timeout, 5xx)
- Binance Square error code mapping (which codes are retriable vs permanent)
- Cashtag priority list — hardcoded in code vs config file
- Hashtag-to-tag mapping (e.g., `tags=["airdrop"]` → `#Airdrop`)
- Publishing worker count (single consumer vs multi-worker)
- Whether to include Telegram message URL in PublishResult
- Draft deduplication before publish (check if already published)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### System Architecture
- `AI-SPEC.md` §3 — Data flow architecture, the Distribution stage (Mode Gate → Publisher)
- `AI-SPEC.md` §4 — Module structure, `publisher.py` responsibility, `PublishResult` model reference
- `AI-SPEC.md` §5.4 — Queue management, publish queue consumption pattern
- `AI-SPEC.md` §7.3 — Telegram output format (markdown structure, emoji guidelines)
- `AI-SPEC.md` §7.4 — Binance Square output format, cashtag rules, hashtag rules
- `AI-SPEC.md` §9 — Guardrails: content length checks, duplicate detection

### Data Models & Config
- `src/models.py` — `DraftContent` with `telegram_markdown`, `binance_square_markdown`, `status`, `tags` fields
- `src/config.py` — `BINANCE_SQUARE_API_KEY`, `TELEGRAM_CHANNEL_ID`, `TELEGRAM_BOT_TOKEN` config keys

### Prior Phase Contracts
- `.planning/phases/03-bot-reviewer/03-CONTEXT.md` — Phase 3 decisions (publish_queue handoff, approval flow)
- `src/bot_reviewer.py` — Approved drafts put on `publish_queue`, consumer not yet wired
- `src/main.py` — `publish_queue: asyncio.Queue[DraftContent]` created and wired through bot reviewer

### Established Patterns (Reuse)
- `src/ai_handler.py` — `OpenRouterClient` pattern (httpx client injection, async worker, error handling)
- `src/ai_handler.py` — `AIConsumer` pattern (queue consumer, shutdown event, worker lifecycle)
- `src/ai_handler.py` — `TokenBucket` rate limiter (if needed for rate limiting)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ai_handler.py` `OpenRouterClient` — httpx-based API caller pattern (header auth, POST, error handling) directly reusable for Binance Square API calls
- `src/ai_handler.py` `AIConsumer` — async worker pattern (queue consumer, shutdown event, backpressure logging) directly reusable for publisher consumer
- `src/main.py` — Shared `httpx.AsyncClient` can be extended and injected into publisher
- `src/logging_setup.py` — Structured logging with `logger.exception()`, reusable by publisher module

### Established Patterns
- Pydantic v2 `BaseModel` for all data models (PublishResult will follow this)
- Async/await throughout with asyncio
- Module-per-responsibility pattern in `src/`
- Queue consumer pattern (producer → queue → consumer) established across all prior phases
- httpx.AsyncClient injected from main.py, not created per-module

### Integration Points
- `publish_queue: asyncio.Queue[DraftContent]` in `main.py` — approved drafts go here, publisher must consume
- `src/main.py` — Must create publisher consumer and register task alongside crawler + AI + bot reviewer
- `src/config.py` — `BINANCE_SQUARE_API_KEY` and `TELEGRAM_CHANNEL_ID` already available, no new config keys needed
- `src/models.py` — Must add `PublishResult` model; `DraftContent.status` already supports `"published"` literal
- `src/bot_reviewer.py` — Already puts approved drafts on `publish_queue` (both via manual approve and AUTO mode)

</code_context>

<specifics>
## Specific Ideas

- Binance Square API requires `clienttype: binanceSkill` header alongside the API key
- Post URL for successful Binance Square post: `https://www.binance.com/square/post/{data.id}`
- Daily post limit: ~100 posts/day per API key (error code 220009)
- Telegram sendMessage via Bot API supports MarkdownV2 or HTML parsing — mirrors PTB's existing send_message defaults
- Cashtag priority list per AI-SPEC §7.4: $BTC, $ETH, $SOL, $ARB, $OP, $MATIC, $AVAX, $ATOM

</specifics>

<deferred>
## Deferred Ideas

- Media/image support for Binance Square posts — not supported by API in v1
- Scheduled/delayed publishing — separate feature
- Publish queue persistence across restarts — database-backed queue
- Auto-retry with exponential backoff for failed platforms — enhancement beyond v1
- Multi-worker publisher for higher throughput — single worker sufficient for ~100 posts/day Binance limit

</deferred>

---

*Phase: 04-publisher*
*Context gathered: 2026-05-17*
