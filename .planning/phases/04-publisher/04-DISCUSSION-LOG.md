# Phase 4: Publisher & Platform Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 04-publisher
**Areas discussed:** Telegram publish method, Binance Square API approach, Cashtag/Hashtag strategy, Publish reliability & partial failure, PublishResult tracking model, Publishing rate limiting

---

## Telegram Publish Method

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse PTB bot (Recommended) | Use application.bot.send_message(chat_id=config.telegram_channel_id) — no new connection, no new dependency. Bot must be admin in target channel. | ✓ |
| Telethon TelegramClient | Use existing Telethon client from crawler.py. More feature-rich but shares connection with crawler — potential cross-contamination. | |
| Direct Bot API via httpx | Call https://api.telegram.org/bot{token}/sendMessage via httpx. No library dependency but needs manual endpoint handling. | |

**User's choice:** Reuse PTB bot
**Notes:** Bot must be admin in the target Telegram channel

---

## Binance Square API Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Direct httpx (Recommended) | Simple POST via shared httpx.AsyncClient — follows same pattern as OpenRouter calls in ai_handler.py. No new dependency. Map error codes to structured results. | ✓ |
| Wrap in dedicated client class | Create a BinanceSquareClient class with its own error handling, retry logic, and rate limit awareness. More structured but more code. | |

**User's choice:** Direct httpx
**Notes:** Endpoint: POST https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add. Headers: X-Square-OpenAPI-Key, Content-Type: application/json, clienttype: binanceSkill. Body: {"bodyTextOnly": "..."} Text-only, ~100 posts/day limit.

---

## Cashtag / Hashtag Injection Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Last-minute injector (Recommended) | Strip existing tags from AI output, inject deterministically based on DraftContent.tags + coin→cashtag mapping. Clean separation — AI writes content, injector handles formatting compliance. | ✓ |
| AI assigns, injector validates | Let Phase 2 AI include hashtags/cashtags. Injector validates they exist and fills gaps if missing. Less code but AI may be inconsistent. | |
| Configurable mapping file | Same as (a) but coin→cashtag mapping in JSON file so admin can add/remove without code changes. | |

**User's choice:** Last-minute injector
**Notes:** Cashtag priority list per AI-SPEC §7.4: $BTC, $ETH, $SOL, $ARB, $OP, $MATIC, $AVAX, $ATOM. Hashtag rules: always #Airdrop, plus category tags, max 5.

---

## Publish Reliability & Partial Failure

| Option | Description | Selected |
|--------|-------------|----------|
| Continue — log failure (Recommended) | Publish to whatever platform succeeds. Log failures, don't retry. Draft status='published' if at least one platform succeeds. | ✓ |
| Retry with backoff | Retry failed platform up to 3 times with exponential backoff (like OpenRouter). More reliable but delays posting. | |
| Split status — per-platform tracking | Track separate status per platform. Only set published when BOTH succeed. Allows selective retry. | |

**User's choice:** Continue — log failure
**Notes:** Simplest and most resilient approach for v1

---

## PublishResult Tracking Model

| Option | Description | Selected |
|--------|-------------|----------|
| Per-platform results (Recommended) | List[PublishResult] — each with platform, success bool, url, error. One failure doesn't shadow the other's success. | ✓ |
| Single combined result | One PublishResult per draft with single success/error. Simpler but loses granularity. | |

**User's choice:** Per-platform results
**Notes:** Model fields: platform (telegram/binance_square), success, url (optional), error (optional)

---

## Publishing Rate Limiting

| Option | Description | Selected |
|--------|-------------|----------|
| Simple cooldown (Recommended) | 2-second delay between each draft's platform publishes (Telegram + Binance Square). Enough to stay under both API limits. | ✓ |
| Reuse TokenBucket | Same pattern from Phase 2. 1 token per publish, refill every 2 seconds. More precise but overkill. | |
| No rate limiting | Send immediately, handle 429 errors reactively. Simplest but riskier during burst. | |

**User's choice:** Simple cooldown
**Notes:** Consistent cooldown is sufficient — Binance limits to ~100 posts/day

---

## the agent's Discretion

- Exact retry count for individual API call errors (connection timeout, 5xx)
- Binance Square error code mapping (which codes are retriable vs permanent)
- Cashtag priority list hardcoded in code vs config file
- Hashtag-to-tag mapping (e.g., tags=["airdrop"] → #Airdrop)
- Publishing worker count
- Whether to include Telegram message URL in PublishResult
- Draft deduplication before publish

## Deferred Ideas

- Media/image support for Binance Square — not supported by API in v1
- Scheduled/delayed publishing — separate feature
- Publish queue persistence across restarts — database-backed queue
- Auto-retry with exponential backoff — enhancement beyond v1
- Multi-worker publisher for higher throughput
