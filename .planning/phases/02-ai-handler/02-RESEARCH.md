# Phase 2: AI Handler & Processing — Research

## OpenRouter API

### Endpoint
`POST https://openrouter.ai/api/v1/chat/completions`
- Auth: `Authorization: Bearer <OPENROUTER_API_KEY>` header
- Content-Type: `application/json`

### Fallback Models (per AI-SPEC §6.2)
| Priority | Model ID | Notes |
|----------|----------|-------|
| Primary | `deepseek-chat:free` | Fast, reliable on free tier |
| Fallback 1 | `meta-llama/llama-3-70b-instruct:free` | Good quality, higher latency |
| Fallback 2 | `qwen/qwen-2.5-72b-instruct:free` | Last resort free model |

### Structured Outputs
OpenRouter supports `response_format` with `json_schema` type for models that support it. For models without native structured output support, use `"response_format": {"type": "json_object"}` with a prompt instructing JSON output + Pydantic validation as fallback.

### OpenRouter-Specific Features
- **Fallback via extra_body**: Pass `"models": ["primary", "backup1", "backup2"]` in `extra_body` to let OpenRouter auto-fallback
- **Provider routing**: Can configure `"provider": {"require_parameters": true}` for consistency
- **Headers**: `HTTP-Referer` and `X-OpenRouter-Title` for app attribution on leaderboards

---

## httpx Async Patterns

### Client Setup
```python
import httpx

async with httpx.AsyncClient(
    timeout=httpx.Timeout(30.0, connect=10.0, read=30.0),
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
) as client:
    response = await client.post(url, json=body, headers=headers)
```

### Error Handling
- `httpx.TimeoutException` — request took too long
- `httpx.HTTPStatusError` — non-2xx response
- `httpx.RequestError` — network-level failure
- Always use `response.raise_for_status()` or check `response.status_code`

### Connection Pooling
- Single `AsyncClient` instance shared across all AI calls
- Created once at startup, closed on shutdown
- `max_connections` should match worker pool size + margin

---

## Token Bucket Rate Limiter

### Core Algorithm (asyncio)
```python
class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity          # max tokens (burst)
        self.tokens = capacity            # current tokens
        self.refill_rate = refill_rate    # tokens per second
        self.last_checked = time.monotonic()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_checked
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_checked = now

    async def acquire(self, tokens: int = 1) -> None:
        while True:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return
            # Wait for enough tokens to accumulate
            wait_time = (tokens - self.tokens) / self.refill_rate
            await asyncio.sleep(wait_time)
```

### Parameters (agent's discretion)
- `capacity`: 10 tokens (burst capacity — allow 10 rapid calls)
- `refill_rate`: 2 tokens/second (average 2 calls per second = 120/min)
- These are conservative for OpenRouter free tier

---

## Worker Pool Architecture

### Pattern
```python
async def worker(
    worker_id: int,
    queue: asyncio.Queue[RawMessage],
    result_queue: asyncio.Queue[DraftContent],
    rate_limiter: TokenBucket,
    client: httpx.AsyncClient,
):
    while True:
        msg = await queue.get()
        await rate_limiter.acquire()
        try:
            draft = await process_message(client, msg)
            await result_queue.put(draft)
        except AllModelsExhausted:
            logger.error(f"Worker {worker_id}: all models exhausted for msg {msg.message_id}")
        finally:
            queue.task_done()
```

### Lifecycle
- Workers created in `asyncio.gather()` during startup
- On shutdown: cancel workers, drain queues
- Each worker shares the same `httpx.AsyncClient` and `TokenBucket`

---

## Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `httpx` | >=0.27,<1 | Async HTTP client for OpenRouter API |
| `pydantic` | >=2.0,<3 (already installed) | JSON validation, DraftContent model |
| (no new dependencies needed beyond these two) |

---

## Important Considerations

1. **2-stage cost**: Each message = 2 API calls (translate + rewrite). With 2-3 workers = 4-6 concurrent API calls. Token bucket must account for this.
2. **JSON validation**: Free models may not reliably produce valid JSON. Always wrap in try/except with Pydantic `model_validate_json()`.
3. **OpenRouter free tier rate limits**: Unofficially ~20 req/min for free models. Token bucket at 2 tokens/sec (120/min) is safe.
4. **Partial failure**: If translate succeeds but rewrite fails, the raw translated text is still usable. Don't lose the work.
5. **Tag-specific prompts**: Store prompts in a dict keyed by tag name. Fallback to a default prompt if tag is unknown.
