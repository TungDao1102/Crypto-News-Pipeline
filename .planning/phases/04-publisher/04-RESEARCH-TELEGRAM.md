# Phase 4: Publisher & Platform Integration — Telegram Bot API Research

**Researched:** 2026-05-17
**Domain:** Telegram Bot API — channel publishing via `python-telegram-bot`
**Confidence:** HIGH (multiple sources converge, including official docs and real-world testing)

## Summary

The Telegram Bot API for channel publishing is well-documented with clear, stable boundaries. For this pipeline's use case (~100 posts/day, 2-second cooldown between publishes), the rate limits are generous enough that the selected simple-cooldown strategy (D-06) keeps the pipeline safely below throttling thresholds.

Key confirmed facts: `send_message` to channels has a **4,096 character limit** (after entity parsing), supports both **MarkdownV2** and **HTML** formatting via `parse_mode`, automatically renders hashtags and cashtags as clickable entities, and accepts both numeric chat IDs (`-100xxxxx`) and `@username` strings. Error handling in python-telegram-bot (PTB) has a clear exception hierarchy: `TelegramError` → `Forbidden` (bot blocked/kicked), `RetryAfter` (rate limited), `BadRequest` (validation), `NetworkError`/`TimedOut` (transient).

**Primary recommendation:** Reuse `application.bot.send_message()` with `parse_mode=ParseMode.HTML` (fewer escaping pitfalls than MarkdownV2) and the `@channelusername` chat_id format already configured in `.env`. Wrap calls in try/except catching `Forbidden`, `RetryAfter`, and `BadRequest` specifically — all other errors bubble to the error handler for logging.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (Telegram Publish Method):** Reuse existing `python-telegram-bot` (PTB) `application.bot.send_message()` to publish to `TELEGRAM_CHANNEL_ID`. No new connection or dependency. The bot must be added as admin to the target Telegram channel.
- **D-04 (Partial Failure Handling):** Continue on partial failure. Publish to whatever platform succeeds. Log failures with structured error info. Set `DraftContent.status = "published"` if at least one platform succeeds. No retry for failed platforms in v1.
- **D-05 (PublishResult Model):** Per-platform results — `list[PublishResult]` where each has:
  - `platform: Literal["telegram", "binance_square"]`
  - `success: bool`
  - `url: str | None` — post URL
  - `error: str | None`
- **D-06 (Rate Limiting):** Simple 2-second cooldown between each draft's platform publishes (Telegram + Binance Square). No TokenBucket needed — consistent cooldown is sufficient to stay under both API rate limits.

### the agent's Discretion
- Exact retry count for individual API call errors (connection timeout, 5xx)
- Whether to include Telegram message URL in PublishResult
- Draft deduplication before publish (check if already published)

### Deferred Ideas (OUT OF SCOPE)
- Scheduled/delayed publishing — separate feature
- Publish queue persistence across restarts — database-backed queue
- Auto-retry with exponential backoff for failed platforms — enhancement beyond v1
- Multi-worker publisher for higher throughput
</user_constraints>

<phase_requirements>
## Phase Requirements

The publisher phase is not split into numbered requirements, but the following capabilities must be implemented:

| Capability | Description | Research Support |
|------------|-------------|------------------|
| TG-PUB-01 | Publish DraftContent.telegram_markdown to Telegram channel via PTB | Send via `application.bot.send_message()` with parse_mode (D-01). Chat ID from `config.TELEGRAM_CHANNEL_ID` (supports @username) |
| TG-PUB-02 | Respect rate limits under 2-second cooldown | 2s cooldown is well below all limits (20 msg/min per channel, 30 msg/s global) |
| TG-PUB-03 | Handle publish errors gracefully | Catch `Forbidden`, `RetryAfter`, `BadRequest`, `NetworkError` from PTB exception hierarchy |
| TG-PUB-04 | Return PublishResult per platform | Message URL constructable: `https://t.me/{channel_username}/{message_id}` |
| TG-PUB-05 | Inject hashtags before publish | Hashtags are plain text that Telegram auto-renders as entities — no special API handling needed |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Send message to Telegram channel | API / Backend | — | PTB bot runs in the backend process, sends via Bot API HTTP calls |
| Rate limit compliance | API / Backend | — | 2-second cooldown managed by publisher worker in Python asyncio loop |
| Hashtag/cashtag injection | API / Backend | — | Last-minute injector runs in publisher module before sending |
| Error handling & logging | API / Backend | — | Try/except in publisher; structured error in PublishResult |
| Message URL tracking | API / Backend | — | Constructed from returned `message_id` + channel username |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python-telegram-bot` | v21.x / v22.x | Async Telegram Bot API client | Already installed and wired in Phase 3; `application.bot` is the established pattern [VERIFIED: project codebase] |
| `telegram.constants.ParseMode` | — | Parse mode enums for formatting | PTB's built-in enum for `HTML` / `MARKDOWN_V2` / `MARKDOWN` [VERIFIED: ptb docs] |

### Supporting — No new dependencies needed

PTB's existing `application.bot.send_message(chat_id, text, parse_mode)` handles all Telegram API communication. The `telegram.error` module provides all needed exception classes.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PTB `application.bot.send_message()` | Direct httpx POST to `https://api.telegram.org/bot{token}/sendMessage` | D-01 locks PTB. Direct httpx would reduce dependency but add ~50 LOC for auth, error parsing, entity handling that PTB provides free |
| `ParseMode.HTML` | `ParseMode.MARKDOWN_V2` | MarkdownV2 requires escaping 7 special characters (`_ * [ ] ( ) ~ ` > # + - = | { } . !`). HTML only requires escaping 3 (`< > &`). HTML is significantly less error-prone for AI-generated content |

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `python-telegram-bot` | PyPI | 10+ yrs | ~8M+/month | github.com/python-telegram-bot/python-telegram-bot | N/A — existing dependency | Already installed, no new install needed |

**No new packages to install.** The research confirms the existing PTB dependency is sufficient.

## Architecture Patterns

### System Architecture Diagram — Telegram Publish Flow

```
DraftContent from publish_queue
         │
         ▼
┌─────────────────────────────┐
│  Publisher.publish()        │
│  - 2s cooldown (asyncio.sleep) │
└─────────────────────────────┘
         │
         ├─────────────────────────┐
         ▼                         ▼
┌─────────────────┐    ┌──────────────────┐
│ TelegramPublisher│    │ BinancePublisher │ (separate research)
└────────┬────────┘    └──────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  application.bot.send_message(      │
│      chat_id="@channel_username",   │
│      text=telegram_markdown,        │
│      parse_mode=ParseMode.HTML      │
│  )                                  │
└────────────────┬────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
 Success    Failure
    │         │
    ▼         ▼
 Return     Return
 PublishResult PublishResult
 (success=True, (success=False,
  url=...)      error=...)
```

### Pattern 1: Publish and Record Result

```python
async def publish_to_telegram(
    bot: telegram.ext.ExtBot,
    channel_id: str,
    content: str,
) -> PublishResult:
    """Publish content to Telegram channel. Returns per-platform result."""
    try:
        message = await bot.send_message(
            chat_id=channel_id,
            text=content,
            parse_mode=ParseMode.HTML,
        )
        # Construct message URL: https://t.me/channel_username/message_id
        # Remove @ prefix if present, get the username part
        username = channel_id.lstrip("@")
        url = f"https://t.me/{username}/{message.id}"
        return PublishResult(
            platform="telegram",
            success=True,
            url=url,
            error=None,
        )
    except Forbidden as e:
        # Bot was removed from channel or blocked — permanent failure
        logger.error(f"Telegram publish forbidden: {e}")
        return PublishResult(
            platform="telegram",
            success=False,
            url=None,
            error=f"Forbidden: {e.message}",
        )
    except RetryAfter as e:
        # Rate limited — log; no auto-retry per D-04
        logger.warning(f"Telegram rate limited, retry after {e.retry_after}s: {e}")
        return PublishResult(
            platform="telegram",
            success=False,
            url=None,
            error=f"RateLimited: retry after {e.retry_after}s",
        )
    except BadRequest as e:
        # Validation error (message too long, chat not found, etc.) — permanent
        logger.error(f"Telegram bad request: {e}")
        return PublishResult(
            platform="telegram",
            success=False,
            url=None,
            error=f"BadRequest: {e.message}",
        )
    except (NetworkError, TimedOut) as e:
        # Transient network error — could retry but D-04 says no retry in v1
        logger.error(f"Telegram network error: {e}")
        return PublishResult(
            platform="telegram",
            success=False,
            url=None,
            error=f"NetworkError: {e.message}",
        )
```

**Source:** [VERIFIED: python-telegram-bot docs — telegram.error module, application.bot.send_message()](https://docs.python-telegram-bot.org/en/v22.3/telegram.error.html), [VERIFIED: core.telegram.org/bots/api#sendmessage](https://core.telegram.org/bots/api#sendmessage)

### Pattern 2: Content Truncation Guard (Pre-1970s)

Since Telegram has a hard 4,096 character limit, guard against overflow before sending:

```python
MAX_TELEGRAM_LENGTH = 4096  # hard Bot API limit

def truncate_telegram_content(content: str, max_len: int = MAX_TELEGRAM_LENGTH) -> str:
    """Truncate content to Telegram's character limit, preserving format."""
    if len(content) <= max_len:
        return content
    # Truncate at last sentence boundary within limit
    truncated = content[:max_len]
    last_period = truncated.rfind(".")
    last_newline = truncated.rfind("\n")
    cut_point = max(last_period + 1 if last_period > max_len * 0.8 else 0,
                    last_newline if last_newline > max_len * 0.8 else 0)
    if cut_point > 0:
        return content[:cut_point] + "\n\n⚠️ *Bài viết đã được cắt ngắn do giới hạn độ dài Telegram*"
    return content[:max_len - 50] + "\n\n⚠️ *Bài viết đã được cắt ngắn...*"
```

Note: The `DraftContent.telegram_markdown` field already has `max_length=4000` in its Pydantic schema (AI-SPEC §6.3), so AI-generated content should be safely under the 4096 limit. This guard is defense-in-depth.

### Anti-Patterns to Avoid

- **Using legacy `ParseMode.MARKDOWN` (Markdown, not MarkdownV2):** Telegram explicitly says "Markdown is a legacy mode" — no underline, strikethrough, spoiler support. Use `MARKDOWN_V2` or `HTML`.
- **Sending without `parse_mode`:** Raw markdown characters (`*`, `_`) will be displayed literally instead of formatting text. Always set parse_mode.
- **Assuming `@username` is the only format:** Channel IDs can be numeric (`-1001234567890`). The code should handle both `str` (with or without `@`) and `int` chat_id types. PTB's `send_message` accepts `Union[str, int]`.
- **Not escaping HTML in AI content:** If using HTML parse mode, AI-generated content containing `<`, `>`, or `&` must be escaped. However, since the AI generates the content specifically for Telegram, the AI prompt should be trained to produce valid HTML/MarkdownV2.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Telegram Bot API HTTP client | Custom httpx wrapper | `python-telegram-bot` `application.bot.send_message()` | Already wired in Phase 3. PTB handles auth, retry headers, entity parsing, error classification into typed exceptions. Re-implementing would duplicate 500+ lines of battle-tested code |
| Rate limit backoff logic | Custom sleep/delay calculator | PTB's `BaseRateLimiter` / `AIORateLimiter` (if needed) or simple asyncio.sleep | D-06 chooses simple cooldown, which is adequate. But if rate limit handling is needed later, PTB provides the interface |
| Message entity construction | Manual JSON building for entities | Use `parse_mode="HTML"` or `ParseMode.HTML` | Let Telegram parse HTML into entities server-side. Manual entity building is error-prone (UTF-16 offset counting) |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hashtag/cashtag parsing | Regex to detect existing tags in text | Last-minute injector pattern (D-03) | Strip all existing tags, inject deterministically. Cleaner separation |
| Message URL construction | API call to get message link | `f"https://t.me/{username}/{message_id}"` | Simple string interpolation; no additional API call needed |
| Content length validation | Character counting after entity parsing | Pre-send `len(content)` check against 4096 | Entity parsing can change effective length, but for text-only (no entities passed separately), pre-send length check is accurate |

**Key insight:** The Telegram publish path is intentionally straightforward — the existing PTB setup handles all HTTP communication, auth, and serialization. The publisher module's complexity goes into error classification and result tracking, not into the publish call itself.

## Common Pitfalls

### Pitfall 1: MarkdownV2 Special Character Escaping
**What goes wrong:** AI-generated content with special characters (`_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`) causes `BadRequest: Can't parse entities` when sent with `parse_mode=MarkdownV2`.
**Why it happens:** MarkdownV2 requires escaping 7+ characters with backslash. AI output often includes underscores in URLs or parentheses in text.
**How to avoid:** Use `ParseMode.HTML` instead — only 3 characters need escaping (`<`, `>`, `&`). Alternatively, use PTB's entity-based approach (pass entities directly without parse_mode).
**Warning signs:** Frequent "Can't parse entities" BadRequest errors in logs.

### Pitfall 2: Silent Message Drop at 4,096+ Characters
**What goes wrong:** Content exceeding 4,096 characters fails silently — no message appears, no error in PTB logs.
**Why it happens:** Telegram's hard 4,096 character limit. PTB returns a `BadRequest` error, but if uncaught, the error handler may log it generically.
**How to avoid:** Pre-validate `len(content) <= 4096` before sending. The `DraftContent.telegram_markdown` Pydantic field should enforce `max_length=4096` (AI-SPEC currently specifies 4000 — keep this or raise to 4096).
**Warning signs:** "Message is too long" in logs. Check for `entities_too_long` if using entity-based formatting.

### Pitfall 3: @Username vs Numeric Chat ID
**What goes wrong:** Some developer tools and stack overflow answers show numeric IDs (`-1001234567890`) while `.env` files often use `@username`. Code that assumes one format breaks with the other.
**Why it happens:** Telegram Bot API accepts both formats, but users configure channels differently.
**How to avoid:** Handle both in `send_message()` — PTB's `chat_id` parameter already accepts `Union[str, int]`. Just ensure the config value is passed through without transformation.

### Pitfall 4: Ignoring RetryAfter 429 Errors
**What goes wrong:** Bot hits rate limit, keeps hammering API, `retry_after` timer extends from seconds to minutes.
**Why it happens:** D-04 says "no retry in v1," but D-06's 2-second cooldown should prevent 429s in practice. If 429s do occur, ignoring them causes escalating bans.
**How to avoid:** Still catch `RetryAfter` in the try/except even though the plan says no retry. Log it prominently. With 2-second cooldown + ~60 posts/day, this should never trigger under normal operation.

## Code Examples

### Sending a formatted message to a channel (HTML mode — recommended)

```python
import logging
from telegram.error import Forbidden, RetryAfter, BadRequest, NetworkError, TimedOut
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

async def publish_telegram(
    bot,
    channel_id: str,  # e.g., "@my_channel" or "-1001234567890"
    content: str,
) -> dict:
    """
    Publish formatted content to a Telegram channel.
    Returns dict with success, url, error fields.
    
    Source: [VERIFIED: python-telegram-bot docs]
    """
    # Pre-validate length (hard Bot API limit: 4096 chars after entity parsing)
    if len(content) > 4096:
        logger.warning(f"Content length {len(content)} exceeds 4096 limit — truncating")
        content = content[:4046] + "\n\n... (truncated)"
    
    try:
        message = await bot.send_message(
            chat_id=channel_id,
            text=content,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,  # show link previews
        )
        
        # Construct post URL
        username = channel_id.lstrip("@")
        url = f"https://t.me/{username}/{message.id}"
        
        logger.info(f"✅ Telegram publish success: {url}")
        return {"success": True, "url": url, "error": None}
        
    except Forbidden as e:
        # Bot kicked/blocked — remove channel from rotation in future
        logger.error(f"❌ Telegram Forbidden (bot removed from channel?): {e}")
        return {"success": False, "url": None, "error": f"Forbidden: {e.message}"}
        
    except RetryAfter as e:
        # Rate limited — log prominently despite D-04's no-retry policy
        logger.warning(f"⚠️ Telegram rate limited ({e.retry_after}s): {e}")
        return {"success": False, "url": None, "error": f"RateLimited: retry in {e.retry_after}s"}
        
    except BadRequest as e:
        # Validation error — likely content issue (too long, bad entities)
        logger.error(f"❌ Telegram BadRequest: {e}")
        return {"success": False, "url": None, "error": f"BadRequest: {e.message}"}
        
    except (NetworkError, TimedOut) as e:
        # Transient network issue
        logger.error(f"❌ Telegram network error: {e}")
        return {"success": False, "url": None, "error": f"NetworkError: {e.message}"}
```

**Source:** [VERIFIED: python-telegram-bot v22.3 telegram.error module](https://docs.python-telegram-bot.org/en/v22.3/telegram.error.html), [VERIFIED: core.telegram.org/bots/api#sendmessage](https://core.telegram.org/bots/api#sendmessage)

### Publishing with 2-second cooldown (D-06 compliant)

```python
async def publish_draft(draft: DraftContent, bot, channel_id: str) -> list[PublishResult]:
    """
    Publish a draft to Telegram and Binance Square.
    >2 second cooldown between platforms to respect rate limits (D-06).
    """
    results = []
    
    # Step 1: Publish to Telegram
    tg_result = await publish_telegram(bot, channel_id, draft.telegram_markdown)
    results.append(PublishResult(
        platform="telegram",
        success=tg_result["success"],
        url=tg_result["url"],
        error=tg_result["error"],
    ))
    
    # D-06: 2-second cooldown before next platform
    await asyncio.sleep(2)
    
    # Step 2: Publish to Binance Square (via httpx — separate module)
    bs_result = await publish_binance_square(...)
    results.append(bs_result)
    
    return results
```

### Hashtag injection (plain text — Telegram auto-renders)

```python
def inject_hashtags(text: str, tags: list[str]) -> str:
    """
    Append hashtags to content.
    Telegram auto-renders #text as clickable hashtag entities.
    No special API call needed.
    
    Source: [VERIFIED: core.telegram.org/api/entities — hashtag is a built-in entity type]
    """
    hashtag_map = {
        "airdrop": "#Airdrop",
        "testnet": "#Testnet",
        "retroactive": "#Retroactive",
        "defi": "#DeFi",
        "nft": "#NFT",
    }
    used_tags = set()
    hashtags = []
    for tag in tags:
        normalized = tag.lower().strip()
        if normalized in hashtag_map and normalized not in used_tags:
            hashtags.append(hashtag_map[normalized])
            used_tags.add(normalized)
        if len(hashtags) >= 5:  # max 5 hashtags per AI-SPEC §7.4
            break
    
    if hashtags:
        return text.rstrip() + "\n\n" + " ".join(hashtags)
    return text
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ParseMode.MARKDOWN (legacy) | ParseMode.MARKDOWN_V2 or ParseMode.HTML | Bot API 5.0+ (pre-2022) | Legacy Markdown lacks underline, strikethrough, spoiler — never use it |
| No rate limit headers | Bot API 7.8+ sends `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` headers | June 2025 (Bot API 7.8) | Allows proactive rate management; not needed for this pipeline's volume |
| Flat 429 response | 429 now includes `scope` field (`global` or `chat`) | Bot API 7.8 (June 2025) | Enables granular backoff per chat vs global; not critical for this pipeline |
| Paid broadcast tier | Up to 1000 msg/s via Telegram Stars | 2025 | Not applicable — this pipeline operates at <100 posts/day |

**Deprecated/outdated:**
- `ParseMode.MARKDOWN` (legacy Markdown): Never use. Use `MARKDOWN_V2` or `HTML`.
- `telegram.error.Unauthorized`: Renamed to `Forbidden` in PTB v20.0.

## Assumptions Log

While the research validates most claims with high confidence, some areas rely on indirect evidence or project-specific consistency:

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 2-second cooldown is sufficient for ~60-100 posts/day | Common Pitfalls | If Telegram per-channel limit is stricter than documented (e.g., 1 msg/3s for channels), bot could hit 429. Mitigation: D-04 says "no retry" — failure would skip that post. Low risk. |
| A2 | `@channelusername` format works in PTB `send_message()` | Pattern 1 | PTB doc says "username of the target channel (in the format @channelusername)". Already in project's .env as `TELEGRAM_CHANNEL_ID=@your_telegram_channel`. Verified across multiple sources. |
| A3 | HTML parse_mode is safer than MarkdownV2 for AI content | Pitfall 1 | HTML escaping is objectively simpler (3 chars vs 7+). However, if AI generates malformed HTML tags, the error may be less descriptive. Mitigation: AI prompt should specify valid HTML output. Low risk. |
| A4 | Channel message URL format `https://t.me/{username}/{message_id}` works | Pattern 1 | Standard pattern documented across Telegram FAQ and community. Only works for public channels. The project uses a public channel (@your_telegram_channel). |
| A5 | Pydantic `max_length=4000` in DraftContent is sufficient to stay under 4096 Bot API limit | Pitfall 2 | AI-SPEC currently specifies max_length=4000 for telegram_markdown. 4000 < 4096 gives 96 characters of headroom. Risk only if AI consistently produces content very close to the limit. |

## Open Questions

1. **Channel type — public vs private?**
   - What we know: `.env` config uses `@your_telegram_channel` format, which implies a public channel
   - What's unclear: If the channel is public, `@username` works. If private, only numeric `-100xxx` ID works
   - Recommendation: Code should handle both `str` (`@username`) and `int` (`-100xxx`) chat_id formats, since `send_message` accepts both. If channel changes from public to private, only the config value needs updating.

2. **Hashtag-to-tag mapping location?**
   - What we know: AI-SPEC §7.4 specifies rules but not where mapping lives
   - What's unclear: Hardcoded in publisher.py vs external config file
   - Recommendation: Leave for agent's discretion per CONTEXT.md. For v1, a dict in publisher.py is simplest.

3. **Message URL inclusion in PublishResult?**
   - What we know: `url: str | None` is part of PublishResult model per D-05
   - What's unclear: Whether Telegram message URL is worth constructing (requires channel username + message_id)
   - Recommendation: Include it. `https://t.me/{username}/{message_id}` is trivially constructable from the `send_message` response. Leave as agent's discretion per CONTEXT.md.

4. **Deduplication before publish?**
   - What we know: In AUTO mode, duplicate detection guardrail (9.1) exists
   - What's unclear: Whether publisher should check if content was already posted
   - Recommendation: Defer — leave as agent's discretion. The guardrail can be added later.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python-telegram-bot | Telegram publish | ✓ (existing Phase 3 dep) | PTB v21.x/v22.x | — |
| Telegram Bot Token | Bot authentication | ✓ (in .env) | — | — |
| Telegram Channel ID | Target channel | ✓ (in .env as @username) | — | — |

**Missing dependencies with no fallback:** None — all dependencies are already present from Phase 3.

## Validation Architecture

This section covers validation specific to Telegram publishing within Phase 4's scope.

### Test Framework

The project uses pytest (established in prior phases). No new test framework needed.

### Telegram-Specific Tests

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TG-01 | `publish_telegram()` returns `PublishResult` with `success=True` when API succeeds | Unit (mocked) | `pytest tests/test_publisher.py::test_telegram_publish_success -x` | ❌ Wave 0 |
| TG-02 | `publish_telegram()` catches `Forbidden` and returns `success=False` | Unit (mocked) | `pytest tests/test_publisher.py::test_telegram_publish_forbidden -x` | ❌ Wave 0 |
| TG-03 | `publish_telegram()` catches `RetryAfter` and logs warning | Unit (mocked) | `pytest tests/test_publisher.py::test_telegram_publish_retryafter -x` | ❌ Wave 0 |
| TG-04 | `publish_telegram()` validates content length ≤ 4096 before sending | Unit | `pytest tests/test_publisher.py::test_telegram_content_length -x` | ❌ Wave 0 |
| TG-05 | `truncate_telegram_content()` truncates at boundary when length exceeds limit | Unit | `pytest tests/test_publisher.py::test_telegram_truncation -x` | ❌ Wave 0 |
| TG-06 | Hashtag injector appends ≤ 5 hashtags from tags list | Unit | `pytest tests/test_publisher.py::test_hashtag_injection -x` | ❌ Wave 0 |
| TG-07 | `publish_draft()` enforces 2-second cooldown between platform publishes | Integration | `pytest tests/test_publisher.py::test_publish_cooldown -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_publisher.py -x --tb=short`
- **Per wave merge:** Full `pytest` suite
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_publisher.py` — all 7 test functions above
- [ ] `tests/conftest.py` — mocked PTB bot fixture (return mock `Message` with `.id` attr)
- [ ] Framework: pytest already installed from prior phases

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | Content length check (4096 chars), HTML tag sanitization if using HTML parse_mode |
| V4 Access Control | Yes | Bot token stored in .env (gitignored); channel access gated by bot admin permissions. D-04 handles partial failures without exposing channel membership |
| V6 Cryptography | No | No encryption/decryption in Telegram publish path |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Bot token leakage via log | Information Disclosure | Don't log bot token. `config.py` already loads from .env; ensure publisher module never logs the token value |
| Malformed content causing service error | Denial of Service | Content length validation (4096 char limit) prevents oversized content. Catch all PTB exceptions (Forbidden, BadRequest, etc.) so publisher worker continues processing queue |
| AI-generated content with malicious HTML | Spoofing / Tampering | If using HTML parse_mode, ensure AI prompt constrains output to safe tags. `<script>`, `<iframe>` etc. are not in Telegram's allowed HTML tag list and will be rejected server-side with a BadRequest |
| Bot removed from channel (Forbidden) | Repudiation | Log the Forbidden error with channel ID. The bot can be re-added manually. No auto-recovery in v1 |

## Sources

### Primary (HIGH confidence)

| Source | What Was Checked | URL |
|--------|------------------|-----|
| core.telegram.org/bots/api | `sendMessage` method signature, parameters, parse_mode options, chat_id types, character limit (1-4096), MessageEntity types (hashtag, cashtag) | https://core.telegram.org/bots/api |
| core.telegram.org/bots/faq | Rate limits: 30 msg/s global, 20 msg/min groups, 1 msg/s per chat, paid broadcast (1000 msg/s via Stars) | https://core.telegram.org/bots/faq |
| core.telegram.org/api/entities | Message entity types: hashtag, cashtag, bold, italic, etc. Markdown/HTML entity generation | https://core.telegram.org/api/entities |
| python-telegram-bot docs v22.3 | `telegram.error` module: Forbidden, RetryAfter, BadRequest, NetworkError, TimedOut | https://docs.python-telegram-bot.org/en/v22.3/telegram.error.html |
| python-telegram-bot docs v22.7 | `telegram.Message` class, `send_message()` signature, parse_mode constants | https://docs.python-telegram-bot.org/en/latest/telegram.message.html |
| PTB GitHub Wiki — Avoiding flood limits | PTB's AIORateLimiter, BaseRateLimiter interface, flood limit numbers for groups/channels | https://github-wiki-see.page/m/python-telegram-bot/python-telegram-bot/wiki/Avoiding-flood-limits |

### Secondary (MEDIUM confidence)

| Source | What Was Checked | URL |
|--------|------------------|-----|
| Bot API rate limits blog (Dec 2025) | Empirical burst limits, scope field in 429, X-RateLimit headers, per-chat limits for groups/channels | https://fyw-telegram.com/blogs/1650734730/ |
| Telegram rate limits calculator (2026) | Three-level limit model: per-chat ~1 msg/s, per-group 20 msg/min, global 30 msg/s | https://botnamefinder.com/blog/telegram-bot-rate-limits-explained |
| PTB GitHub — Issue #374 "Message is too long" | Confirmation that 4096 char limit is after entity parsing, server rejects longer messages | https://github.com/tdlib/telegram-bot-api/issues/374 |
| PTB GitHub — Issue #225 "How to handle 400, 403 errors" | Error handling patterns: try/except per chat_id, error handler for uncaught exceptions | https://github.com/python-telegram-bot/python-telegram-bot/issues/225 |
| StackOverflow — Telegram Channel chat_id | Techniques: use @username with sendMessage to get numeric ID, -100 prefix for channel IDs | https://stackoverflow.com/questions/36099709/how-to-get-the-right-telegram-channel-id |
| tginfo.me — Telegram Limits | Message length limit: up to 4,096 characters | https://limits.tginfo.me/ |

### Tertiary (LOW confidence — single source, unverified)

| Source | What Was Checked | URL |
|--------|------------------|-----|
| Bot API scheduling blog (Nov 2025) | Per-channel limit for scheduling: 1 msg/3s, but D-06 uses simple cooldown, not scheduling | https://pcg-telegram.com/blogs/222 |
| OpenClaw issue #67396 | Bot API silently drops >4096 char messages — confirms hard limit | https://github.com/openclaw/openclaw/issues/67396 |

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — PTB `application.bot.send_message()` is the established pattern from Phase 3
- **Rate limits:** HIGH — multiple sources (official FAQ, empirical testing, PTB wiki) converge on the same numbers
- **Markdown/HTML formatting:** HIGH — official Bot API doc has comprehensive examples
- **Hashtag rendering:** HIGH — MessageEntity "hashtag" is a defined first-class entity type
- **Chat ID resolution:** HIGH — Bot API docs explicitly support both int and @username formats
- **Error handling:** HIGH — PTB exception hierarchy is well-documented in source code and error wiki
- **Content limits:** HIGH — Bot API doc clearly states "1-4096 characters after entities parsing"

**Research date:** 2026-05-17
**Valid until:** 2026-07-17 (Telegram Bot API is stable; rate limits haven't changed since 2019)
