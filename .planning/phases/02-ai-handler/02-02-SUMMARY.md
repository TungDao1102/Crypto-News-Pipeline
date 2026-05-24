# Plan 02-02 — Text Preprocessor + Rate Limiter + Worker Framework — Summary

## Objective
Build the preprocessing pipeline, token bucket rate limiter, and worker pool scaffolding in `src/ai_handler.py`.

## Tasks Completed

### Task 1: Create src/ai_handler.py with preprocessor
- `TextPreprocessor` class with `preprocess(raw_text) -> str` method
- Strips emoji characters via regex `[\U0001F000-\U0010FFFF]`
- Detects and preserves contract addresses (`0x[a-fA-F0-9]{40}`) and code blocks (triple backticks) via placeholder protection
- Normalizes whitespace (collapses multiple spaces/newlines)
- URLs preserved as-is
- **Commit:** `8bc8148`

### Task 2: Implement TokenBucket rate limiter
- `TokenBucket` class with capacity/refill_rate
- `_refill()` based on `time.monotonic()` elapsed time
- `async def acquire(tokens=1)` — blocks until tokens available, then deducts
- Capacity respected (tokens never exceed capacity)
- **Commit:** `8bc8148`

### Task 3: Create worker framework (AIConsumer scaffolding)
- `AIConsumer` class with references to raw_queue, result_queue, TokenBucket, httpx AsyncClient
- `__init__(raw_queue, result_queue, channel_tags, rate_limiter, http_client, api_key, worker_count=3)`
- `start()` — creates N workers via `asyncio.gather()`
- `shutdown()` — cancels all worker tasks via `asyncio.Event`
- Worker loop: reads from raw_queue, processes, puts to result_queue
- Backpressure WARNING when raw_queue > 10 messages
- **Commit:** `8bc8148`

## Verification
- `python -c "from src.ai_handler import TextPreprocessor, TokenBucket, AIConsumer; print('OK')"` exits 0
- Preprocessor preserves contract addresses and code blocks
- Token bucket allows capacity immediate acquires, blocks on 6th
- All infrastructure components importable

## Key Decisions
- Regex-based emoji stripping with placeholder protection for crypto addresses/code blocks
- TokenBucket with monotonic time for accurate rate limiting
- AIConsumer worker pool with configurable worker count (default 3)
- Backpressure warning at 10+ queued messages (no auto-pause — per D-13)
