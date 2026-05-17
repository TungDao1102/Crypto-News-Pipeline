---
status: testing
phase: 02-ai-handler
source: 02-01-PLAN.md, 02-02-PLAN.md, 02-03-PLAN.md, 02-04-PLAN.md
started: 2026-05-17T00:00:00Z
updated: 2026-05-17T00:00:00Z
---

## Current Test

number: 1
name: DraftContent model fields
expected: |
  DraftContent has 5 fields: title_vn (str), telegram_markdown (str), binance_square_markdown (str), status (pending/approved/rejected/published, default pending), tags (list[str], default []). Can import from src.models.DraftContent and construct with required fields.
awaiting: user response

## Tests

### 1. DraftContent model fields
expected: DraftContent has 5 fields: title_vn (str), telegram_markdown (str), binance_square_markdown (str), status (pending/approved/rejected/published, default pending), tags (list[str], default []). Can import from src.models.DraftContent and construct with required fields.
result: [pending]

### 2. Text preprocessor — emoji stripping
expected: Emoji characters are stripped from input while URLs, contract addresses, and code blocks are preserved. Whitespace is normalized.
result: [pending]

### 3. Text preprocessor — verbatim preservation
expected: Contract addresses (0x[40 hex chars]) and code blocks (triple backticks) are preserved verbatim through preprocessing. Reconstructed accurately after stripping.
result: [pending]

### 4. TokenBucket rate limiter
expected: TokenBucket(capacity=5) allows 5 immediate acquires, blocks 6th until refill. Tokens never exceed capacity. acquire(2) correctly deducts 2 tokens.
result: [pending]

### 5. AIConsumer worker pool creates N workers
expected: AIConsumer.start() creates asyncio.Task for each worker. Shutdown cancels all tasks. Default worker_count=3. Worker loop handles cancellation gracefully.
result: [pending]

### 6. Prompt registry — 5 tag-specific configurations
expected: PROMPT_REGISTRY contains keys: default, airdrop, testnet, macro, defi. Each entry has translate_system, rewrite_system, user_template. prompt_for_tags selects by priority order (airdrop > testnet > macro > defi > default).
result: [pending]

### 7. OpenRouterClient — fallback chain order
expected: OpenRouterClient.call_with_fallback tries models in order: deepseek-chat:free → meta-llama/llama-3-70b-instruct:free → qwen/qwen-2.5-72b-instruct:free. On any error (timeout, HTTP error, parse error), logs warning and tries next. Raises AllModelsExhausted if all fail.
result: [pending]

### 8. OpenRouterClient — structured output
expected: call_structured sends response_format={"type":"json_object"} in request body. Validates response content with provided Pydantic model. Falls back through model chain on validation failure.
result: [pending]

### 9. 2-stage processing flow
expected: _process_message runs: preprocessor → Stage 1 (translate, temp 0.6) → Stage 2 (rewrite, temp 0.7). Each stage acquires a token from rate limiter. Output is DraftContent with tags from channel lookup and status="pending".
result: [pending]

### 10. Partial failure handling (Stage 2 fails)
expected: If Stage 1 (translate) succeeds but Stage 2 (rewrite) exhausts all models, AIConsumer creates DraftContent using translated text for both telegram and binance fields, logs WARNING, returns the DraftContent.
result: [pending]

### 11. Full failure handling (Stage 1 fails)
expected: If Stage 1 (translate) exhausts all models, AIConsumer logs ERROR, returns None (message skipped). Worker continues to next message without crashing pipeline.
result: [pending]

### 12. Backpressure warning
expected: When raw_queue exceeds 10 messages, a WARNING log is emitted with queue size. No pause or throttle is applied. Worker continues processing normally.
result: [pending]

### 13. main.py — crawler + AI consumer run concurrently
expected: main.py creates both raw_queue and result_queue. Creates TokenBucket(capacity=10, refill_rate=2.0). Runs httpx.AsyncClient as context manager. Gathers crawler.start() and ai_consumer.start() concurrently.
result: [pending]

### 14. main.py — graceful shutdown
expected: On SIGINT/SIGTERM, both crawler.shutdown() and ai_consumer.shutdown() are called. httpx client closed via context manager. No unhandled exceptions on shutdown.
result: [pending]

### 15. Imports — all modules load cleanly
expected: python -c "from src.main import main; from src.models import DraftContent, RawMessage; from src.ai_handler import TextPreprocessor, TokenBucket, OpenRouterClient, AIConsumer, PROMPT_REGISTRY, AllModelsExhausted, prompt_for_tags" exits 0 with no ImportError.
result: [pending]

## Summary

total: 15
passed: 0
issues: 0
pending: 15
skipped: 0

## Gaps

[none yet]
