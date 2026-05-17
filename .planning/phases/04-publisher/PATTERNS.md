# Phase 4: Publisher & Platform Integration — Pattern Mapping

**Created:** 2026-05-17
**Source patterns:** `src/ai_handler.py`, `src/bot_reviewer.py`, `src/main.py`, `src/models.py`, `src/config.py`

---

## 1. Modules to Create

### Recommended Structure (sub-package)

```
src/publisher/
├── __init__.py              # publish_draft(), start(), shutdown()
├── base.py                  # BasePublisher abstract class
├── telegram.py              # TelegramPublisher
├── binance_square.py        # BinanceSquareClient + BinanceSquarePublisher
└── tag_injector.py          # TagInjector (shared cashtag/hashtag logic)
```

### Alternative (single module — simpler v1)

`src/publisher.py` — OK for v1 if sub-package feels premature. The research supports either; the sub-package is preferred for SRP.

### Class Inventory

| Class | File | Responsibility |
|-------|------|----------------|
| `BasePublisher` | `src/publisher/base.py` | Abstract interface: `async def publish(content: str) -> PublishResult` |
| `TelegramPublisher` | `src/publisher/telegram.py` | Wraps `application.bot.send_message()`, returns `PublishResult` |
| `BinanceSquareClient` | `src/publisher/binance_square.py` | httpx API wrapper (replicates `OpenRouterClient` pattern) |
| `BinanceSquarePublisher` | `src/publisher/binance_square.py` | Uses `BinanceSquareClient`, handles error classification |
| `TagInjector` | `src/publisher/tag_injector.py` | Strips existing tags, injects deterministic cashtags + hashtags |
| `PublisherConsumer` | `src/publisher/__init__.py` or `src/publisher/consumer.py` | Queue consumer worker (replicates `AIConsumer` pattern) |

---

## 2. Existing Patterns to Replicate

### Pattern A: `OpenRouterClient` → `BinanceSquareClient`

**Source:** `src/ai_handler.py:188-216`

```python
# OpenRouterClient pattern (replicate for BinanceSquareClient)
class OpenRouterClient:
    def __init__(self, api_key: str, http_client: httpx.AsyncClient) -> None:
        self.api_key = api_key
        self.http_client = http_client          # Inject shared client from main.py

    async def call(self, ...) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {"model": model, "messages": messages}
        response = await self.http_client.post(URL, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
```

**What to replicate:**
- Constructor takes `api_key: str` + `http_client: httpx.AsyncClient` (injected from `main.py`)
- Uses `self.http_client.post()` — no client creation inside the class
- Header-based auth (Binance uses `X-Square-OpenAPI-Key` instead of `Authorization: Bearer`)
- Returns `dict` with structured error classification
- **Add:** Error code mapping (retriable vs permanent) as class method

### Pattern B: `AIConsumer` → `PublisherConsumer`

**Source:** `src/ai_handler.py:353-480`

```python
# AIConsumer pattern (replicate for PublisherConsumer)
class AIConsumer:
    def __init__(self, raw_queue, result_queue, ..., http_client, api_key, ...):
        self._shutdown = asyncio.Event()
        self._workers: list[asyncio.Task] = []

    async def start(self) -> None:
        self._workers = [asyncio.create_task(self._worker(i)) for i in range(n)]
        await asyncio.gather(*self._workers)

    async def shutdown(self) -> None:
        self._shutdown.set()
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    async def _worker(self, worker_id: int) -> None:
        while not self._shutdown.is_set():
            msg = await self.queue.get()          # Block until item available
            try:
                qsize = self.queue.qsize()
                if qsize > 10:
                    logger.warning("Backpressure: queue size=%d", qsize)
                result = await self._process(msg)
            except Exception:
                logger.exception("Worker %d: unexpected error", worker_id)
            finally:
                self.queue.task_done()
```

**What to replicate:**
- `asyncio.Event` for shutdown signaling
- `asyncio.create_task` worker pattern
- Backpressure logging (`qsize()` warning)
- `queue.task_done()` in `finally` block
- **Adapt:** Only 1 worker needed (Binance daily limit is ~100 posts, single consumer is sufficient; D-06 cooldown also limits throughput)

### Pattern C: `review_consumer()` queue consumer → `PublisherConsumer` 

**Source:** `src/bot_reviewer.py:143-195`

```python
async def review_consumer(result_queue, application, admin_chat_id):
    while True:
        draft = await result_queue.get()
        try:
            # ... process draft, publish, log ...
            pass
        except Exception:
            logger.exception("Failed to process draft")
```

**What to replicate:**
- Infinite `while True` loop with `await queue.get()`
- Process item fully before getting next (sequential, not concurrent — respects cooldown)
- Wrap processing in try/except with `logger.exception()`

### Pattern D: `Config` dataclass pattern

**Source:** `src/config.py:27-49`

```python
class Config:
    def __init__(self, api_id, api_hash, ..., sources):
        ...
```

No new config keys are strictly needed — `BINANCE_SQUARE_API_KEY` and `TELEGRAM_CHANNEL_ID` already exist. Add new keys only if needed for custom retry counts or cooldown intervals (see §5).

---

## 3. Model Changes

### Add `PublishResult` to `src/models.py`

```python
from typing import Literal, Optional

class PublishResult(BaseModel):
    platform: Literal["telegram", "binance_square"]
    success: bool
    url: str | None = None
    error: str | None = None
```

This matches D-05 in CONTEXT.md. No changes needed to `DraftContent` — its `status` field already supports `"published"`.

### Optional: Add `id` field to `DraftContent`

For deduplication, add an `id` field or use `title_vn` as key:
```python
class DraftContent(BaseModel):
    id: str = ""  # Optional — generated as hash of title if empty
```

---

## 4. Wiring in `main.py`

### Current `main.py` (`src/main.py:19-96`)

```
Queues:    raw_queue → [AIConsumer] → result_queue → [Bot Reviewer] → publish_queue
Consumers: crawler         ai_consumer       bot_task (review_consumer)
```

### After Phase 4 Wiring

```
Queues:    raw_queue → [AIConsumer] → result_queue → [Bot Reviewer] → publish_queue → [Publisher]
Consumers: crawler         ai_consumer       bot_task (review_consumer)        publisher_consumer
```

### Code to Add in `main.py`

```python
# After bot_task creation
publisher_consumer = PublisherConsumer(
    publish_queue=publish_queue,
    system_state=system_state,
    http_client=http_client,
    binance_api_key=config.binance_square_api_key,
    bot=bot_task,  # PTB application.bot — needs access via shared reference
)

# In asyncio.gather, add publisher_consumer.start()
try:
    await asyncio.gather(
        crawler.start(),
        ai_consumer.start(),
        bot_task,
        publisher_consumer.start(),  # NEW
    )
except asyncio.CancelledError:
    pass
finally:
    await shutdown()
```

### Telegram Bot Access Pattern

The publisher needs access to `application.bot` (PTB's bot instance). Two options:

**Option A (Preferred):** Create the publisher after the bot is running and pass `application.bot` via `bot_data`:

```python
# In main.py, after bot_task is created:
# Store bot reference in a shared way, or create publisher inside run_bot
```

**Option B:** Have the publisher create its own PTB `Bot` instance from `bot_token` — simpler but duplicates PTB's connection pool.

**Recommendation:** Move publisher consumer creation into `bot_reviewer.py`'s `run_bot()` after `application` is built, or use `application.bot_data` to share the bot reference.

### Modified `run_bot()` Signal

```python
async def run_bot(token, system_state, admin_chat_id, result_queue, publish_queue):
    application = Application.builder().token(token).post_init(post_init).build()
    application.bot_data["system_state"] = system_state
    application.bot_data["admin_chat_id"] = admin_chat_id
    application.bot_data["result_queue"] = result_queue
    application.bot_data["publish_queue"] = publish_queue

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # Start publisher consumer here — has access to application.bot
    publisher_consumer = PublisherConsumer(
        publish_queue=publish_queue,
        system_state=system_state,
        http_client=http_client,    # Pass from main()
        binance_api_key=config.binance_square_api_key,  # Pass from main()
        bot=application.bot,        # PTB bot instance
    )
    asyncio.create_task(review_consumer(result_queue, application, admin_chat_id))
    asyncio.create_task(publisher_consumer.start())  # NEW

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await publisher_consumer.shutdown()  # NEW
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
```

### PublisherConsumer Interface

```python
class PublisherConsumer:
    def __init__(
        self,
        publish_queue: asyncio.Queue[DraftContent],
        system_state: SystemState,
        http_client: httpx.AsyncClient,
        binance_api_key: str,
        bot: telegram.ext.ExtBot,
        telegram_channel_id: str = "@your_telegram_channel",
    ) -> None: ...

    async def start(self) -> None: ...
    async def shutdown(self) -> None: ...
```

---

## 5. Config Additions

### No New Required Env Vars

The following keys already exist in `config.py` and `.env.example`:

| Env Var | Used By | Already Present |
|---------|---------|-----------------|
| `BINANCE_SQUARE_API_KEY` | `BinanceSquareClient` | ✅ Yes |
| `TELEGRAM_CHANNEL_ID` | `TelegramPublisher` | ✅ Yes |
| `TELEGRAM_BOT_TOKEN` | PTB `application.bot` | ✅ Yes |

### Optional Config Extensions (Agent Discretion)

| Key | Default | Purpose |
|-----|---------|---------|
| `PUBLISH_RETRY_COUNT` | `3` | Max retries for transient API errors |
| `PUBLISH_COOLDOWN_SECONDS` | `2` | Seconds between platform publishes (D-06 value) |
| `MAX_CASHTAGS` | `3` | Max cashtags to inject per post |
| `MAX_HASHTAGS` | `5` | Max hashtags to inject per post |

These can be hardcoded in v1 — add to `config.py` only if runtime configurability is needed.

### Cashtag Priority List

Hardcoded in `tag_injector.py` for v1:

```python
CASHTAG_PRIORITY = ["BTC", "ETH", "SOL", "ARB", "OP", "MATIC", "AVAX", "ATOM"]
MAX_CASHTAGS = 3
```

### Hashtag Mapping

Hardcoded in `tag_injector.py` for v1:

```python
HASHTAG_MAP = {
    "airdrop": "#Airdrop",
    "testnet": "#Testnet",
    "retroactive": "#Retroactive",
    "defi": "#DeFi",
    "nft": "#NFT",
    "gamefi": "#GameFi",
    "layer2": "#Layer2",
    "staking": "#Staking",
}
```

---

## Summary: Pattern-to-Implementation Mapping

| Pattern | Source File | Lines | Target File | Adaptation |
|---------|------------|-------|-------------|------------|
| httpx API wrapper + header auth | `ai_handler.py:188-216` (OpenRouterClient) | 28 | `publisher/binance_square.py:BinanceSquareClient` | Change auth header from `Authorization: Bearer` to `X-Square-OpenAPI-Key` + `clienttype` |
| Error classification | `ai_handler.py:236-298` (call_with_fallback) | 62 | `publisher/binance_square.py` | Map Binance error codes instead of HTTP codes |
| Queue consumer + shutdown | `ai_handler.py:353-412` (AIConsumer) | 59 | `publisher/__init__.py:PublisherConsumer` | 1 worker, sequential publish for cooldown |
| Worker loop + backpressure | `bot_reviewer.py:143-168` (review_consumer) | 25 | `publisher/__init__.py:PublisherConsumer._worker` | Same pattern, different processing |
| Model definition | `models.py:22-29` (DraftContent) | 7 | `models.py:PublishResult` | 4 fields: platform, success, url, error |
| Config loading | `config.py:101-126` (load_config) | 25 | `config.py` | No changes needed — keys already exist |
| Event loop wiring | `main.py:87-92` (asyncio.gather) | 5 | `main.py` | Add `publisher_consumer.start()` to gather |
