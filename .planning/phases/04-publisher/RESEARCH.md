# Phase 4: Publisher & Platform Integration — Consolidated Research

**Synthesized:** 2026-05-17
**Sources:** `04-RESEARCH-BINANCE.md`, `04-RESEARCH-TELEGRAM.md`, `04-RESEARCH-TAGS.md`, `04-CONTEXT.md`, `AI-SPEC.md`

---

## 1. Summary

The Publisher phase delivers approved `DraftContent` objects to two platforms: **Telegram Channel** (via existing `python-telegram-bot` `send_message()` with `ParseMode.HTML`) and **Binance Square** (via direct `httpx` POST to a single OpenAPI endpoint with header-based auth). Both platforms accept plain text with embedded hashtags/cashtags — no media, no complex formatting. The key differences are auth mechanism (PTB bot token vs Binance header key), content length limits (4096 hard for Telegram, ~4000 safe for Binance), and error classification. The tag injector is shared between platforms but must enforce **max 3 cashtags** (Binance Square rule) and **max 5 hashtags**. A 2-second cooldown between platform publishes (D-06) keeps the pipeline well under both API rate limits.

---

## 2. API Surface

### Binance Square

| Property | Value |
|----------|-------|
| **Endpoint** | `POST https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add` |
| **Content-Type** | `application/json` |
| **Auth headers** | `X-Square-OpenAPI-Key: {api_key}`, `Content-Type: application/json`, `clienttype: binanceSkill` |
| **Body** | `{"bodyTextOnly": "content"}` |
| **Success response** | `{"code": "000000", "message": null, "data": {"id": "298177291743282"}}` |
| **Post URL** | `https://www.binance.com/square/post/{data.id}` |
| **Daily limit** | ~100 posts/day (error code `220009` when exceeded) |
| **Burst limit** | None documented |
| **Content limit** | Unknown exact max (keep ≤4000 chars to avoid error `20013`) |
| **Formatting** | Plain text only — no Markdown rendering; `#hashtags` and `$cashtags` are auto-detected |
| **Error codes** | 18 documented (see §4) |

### Telegram

| Property | Value |
|----------|-------|
| **Method** | `application.bot.send_message(chat_id, text, parse_mode)` |
| **Chat ID format** | `@username` (public) or `-100xxxxx` (private) — both supported |
| **Recommended parse_mode** | `ParseMode.HTML` (3 chars to escape: `<` `>` `&` vs 7+ for MarkdownV2) |
| **Content limit** | **Hard 4096 characters** after entity parsing |
| **Rate limits** | ~20 msg/min per channel, 30 msg/s global, 1 msg/s per chat |
| **Auth** | Bot token from `@BotFather`, configured as `TELEGRAM_BOT_TOKEN` in `.env` |
| **Post URL** | `https://t.me/{channel_username}/{message_id}` |
| **Tag rendering** | `#hashtag` and `$cashtag` auto-detected as clickable entities — no parse_mode needed |

---

## 3. Content Formatting

### Markdown Stripping (Binance Square)

Binance Square's API does **not** render Markdown. All content must be plain text before sending:

```python
# Operations performed by MarkdownStripper:
- [text](url) → text              # Link text preserved, URL removed
- # headings → plain text          # Heading markers stripped
- **bold** / *italic* → plain text # Emphasis markers removed
- `code` → code                    # Inline code preserved as text
- ```blocks``` → removed           # Code fences removed entirely
- Horizontal rules removed
- Blockquotes un-wrapped
```

The AI-generated `binance_square_markdown` field MUST be stripped before publishing. Preserve `#hashtags`, `$cashtags`, emoji, bullet lists, paragraph breaks.

### Tag Injection Rules

| Rule | Value | Source |
|------|-------|--------|
| Max cashtags per post | **3** | [Binance FAQ](https://www.binance.info/en/support/faq/detail/3f4940d27ff04748a13e0fc1d3f1598d) |
| Max hashtags per post | **5** | AI-SPEC §7.4 |
| Cashtag format | `$TICKER` uppercase (e.g. `$BTC`, `$ETH`) | Binance Write-to-Earn FAQ |
| Injection position | End of content, after separator | Industry convention |
| Order | Hashtags first, then cashtags, each on their own line | Observed pattern |
| Priority list | `["BTC", "ETH", "SOL", "ARB", "OP", "MATIC", "AVAX", "ATOM"]` | AI-SPEC §7.4 |
| Selection strategy | Match against `DraftContent.tags` + content body; pick top 3 matching by priority; fallback to top 3 if no match | Agent discretion |

### HTML vs MarkdownV2 for Telegram

**Decision: Use `ParseMode.HTML`**

| Factor | HTML | MarkdownV2 |
|--------|------|------------|
| Characters to escape | 3 (`<` `>` `&`) | 7+ (`_ * [ ] ( ) ~ ` > # + - = \| { } . !`) |
| Common failure mode | Malformed HTML tags | Unescaped char in AI content causes `Can't parse entities` |
| Supported in PTB | ✅ `ParseMode.HTML` | ✅ `ParseMode.MARKDOWN_V2` |
| AI content compat | Safer — AI rarely generates raw `<`/`>`/`&` | Risky — AI-generated content routinely includes `_`, `*`, `.` |

**Recommendation:** Configure the AI prompt to output valid HTML subset (no `<script>`, `<iframe>`, etc.). Telegram server-side rejects unsafe tags.

---

## 4. Error Handling

### Binance Square Error Classification

| Category | Codes | Action |
|----------|-------|--------|
| **Success** | `000000` (with optional edge case: missing `data.id`) | Construct URL; log warning if ID missing |
| **Transient / Retriable** | `10004` (network error), HTTP 429/5xx | Retry up to 3 times with 2s delay |
| **Daily Limit** | `220009` | Log warning, skip draft, do not retry same day |
| **Fix Content** | `20002`, `20013`, `20020`, `20022`, `20041`, `220010`, `220011` | Log error, skip draft permanently (same content = same error) |
| **Permanent Failure** | `10005`, `10007`, `30004`, `30008`, `220003`, `220004`, `2000001`, `2000002` | Log critical, stop publishing, alert admin |

### Telegram Error Classification

| Exception | Category | Action |
|-----------|----------|--------|
| `Forbidden` | Permanent — bot removed from channel | Log error, skip draft — alert admin |
| `RetryAfter` | Rate limit — transient | Log warning, skip draft (no retry per D-04) |
| `BadRequest` | Permanent — content invalid | Log error, skip draft — likely content issue |
| `NetworkError` / `TimedOut` | Transient network | Log error, skip draft (no retry per D-04) |

### Shared Policy (D-04)

- Publish to whatever platform succeeds
- Set `DraftContent.status = "published"` if **at least one** platform succeeds
- No retry for failed platforms in v1
- Log all failures with structured `PublishResult.error` and `PublishResult.error_code`

---

## 5. Findings That Change AI-SPEC.md

| # | Finding | AI-SPEC Reference | Impact |
|---|---------|-------------------|--------|
| 1 | **Max 3 cashtags per Binance Square post** (not unlimited) | §7.4 lists 8 coins in priority list with no cap | Injector MUST enforce `MAX_CASHTAGS = 3`; only top 3 matching by priority |
| 2 | **`clienttype: binanceSkill` header required** | §4 publisher description mentions only `X-Square-OpenAPI-Key` | Add third header to all Binance Square API calls |
| 3 | **Use `ParseMode.HTML`, not MarkdownV2, for Telegram** | §7.3 doesn't specify parse_mode | Configure AI prompt for valid HTML; use `ParseMode.HTML` in all `send_message()` calls |
| 4 | **Error code 220009 is NOT retriable** | §4 says "retry 3 times" generally | Add special case: daily limit error should be caught and skipped, not retried |
| 5 | **Binance Square does NOT render Markdown** | §7.4 shows `**bold**`, headings, links in examples | Must strip Markdown from `binance_square_markdown` before publishing. AI-SPEC examples show formatted text that the API cannot render |
| 6 | **Telegram has a hard 4096 char limit** (not ~4000) | §6.3 sets `max_length=4000` for both fields | Defense-in-depth truncation at 4096 needed; consider raising Pydantic limit to 4096 |
| 7 | **Post URL format for both platforms** | §4 mentions `PublishResult.url` but no format | Telegram: `https://t.me/{username}/{message_id}`; Binance: `https://www.binance.com/square/post/{data.id}` |
| 8 | **Tag injection is identical for both platforms** | §7.3 and §7.4 describe separate injection patterns | Both platforms auto-detect `#hashtag` and `$cashtag` from plain text — shared injector function can serve both |
| 9 | **Empty `data.id` on success response** | Not mentioned | Add guard: if `code = "000000"` but `data.id` is missing/null, still mark as successful but set `url = None` |
| 10 | **No burst rate limit on Binance Square** | §4 assumes standard rate limiting | 2-second cooldown (D-06) is confirmed sufficient; no TokenBucket needed for Binance |

---

## 6. Implementation Recommendations

### Architecture

```
src/publishers/
├── __init__.py          # Public API: start_publisher(), shutdown_publisher()
├── base.py              # BasePublisher abstract class
├── telegram.py          # TelegramPublisher (uses PTB application.bot)
├── binance_square.py    # BinanceSquarePublisher (uses httpx, header auth)
└── tag_injector.py      # Shared tag injection logic (cashtags + hashtags)
```

Or, for simpler v1, a single `src/publisher.py` with all classes.

### Code Patterns to Follow

| Pattern | Replicate From | For |
|---------|---------------|-----|
| `OpenRouterClient` (httpx wrapper, header auth, error classification) | `src/ai_handler.py:188-300` | `BinanceSquareClient` — similar async httpx POST with header auth |
| `AIConsumer` (queue consumer, shutdown Event, backpressure logging) | `src/ai_handler.py:353-480` | `PublisherConsumer` — consumes `publish_queue`, calls both publishers, logs results |
| `TokenBucket` (rate limiter) | `src/ai_handler.py:327-346` | NOT needed (D-06 uses simple `asyncio.sleep(2)`), but available if burst limits emerge |
| `review_consumer()` (infinite loop, queue.get, try/except) | `src/bot_reviewer.py:143-195` | Publisher consumer — same queue-consumer-worker pattern |

### Recommended Retry Strategy

| Scenario | Action |
|----------|--------|
| HTTP timeout / connection error | Retry up to 2 more times (3 total) with 2s `asyncio.sleep()` |
| Binance `10004` | Same as above |
| HTTP 429 / 5xx | Same as above |
| Binance `220009` (daily limit) | Log warning, do not retry, skip draft |
| Binance `200xx` content errors | Log error, skip draft, do not retry |
| Binance permanent auth/ban errors | Log CRITICAL, do not retry |
| Telegram `RetryAfter` | Log warning, skip draft, do not retry |
| Telegram `Forbidden` / `BadRequest` | Log error, skip draft, do not retry |
| Telegram `NetworkError` / `TimedOut` | Log error, skip draft (no retry per D-04) |

### Content Preparation Pipeline

```
DraftContent (telegram_markdown, binance_square_markdown)
    │
    ├──► Telegram path:
    │      1. tag_injector.inject(draft.telegram_markdown, draft.tags, platform="telegram")
    │      2. truncate at 4096 with sentence-boundary awareness
    │      3. TelegramPublisher.publish(content, parse_mode=ParseMode.HTML)
    │
    └──► Binance Square path:
           1. strip_markdown(draft.binance_square_markdown)  # remove **, [], headings
           2. tag_injector.inject(stripped, draft.tags, platform="binance_square")  # max 3 cashtags
           3. pre-check length ≤ 4000
           4. BinanceSquarePublisher.publish(content)
```

### Deduplication

Implement in-memory set of published draft IDs to prevent double-publishing (e.g., if same draft appears in queue twice due to race):

```python
_published_ids: set[str] = set()  # Track draft IDs that have been published

def _check_dedup(draft_id: str) -> bool:
    if draft_id in _published_ids:
        return True  # skip
    _published_ids.add(draft_id)
    return False
```

This is in-memory only — queue persistence across restarts is deferred.

---

## Metadata

**Research date:** 2026-05-17
**Valid until:** 2026-08-17 (both APIs are stable; Telegram Bot API is v22.x, Binance OpenAPI is unchanging)
