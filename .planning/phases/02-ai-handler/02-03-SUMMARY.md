# Plan 02-03 — OpenRouter API Caller + 2-Stage Processing + Prompt Registry — Summary

## Objective
Implement the OpenRouter API caller with fallback chain, 2-stage processing (translate → rewrite), tag-specific prompt registry, and complete `_process_message` pipeline.

## Tasks Completed

### Task 1: Implement prompt registry with tag-specific prompts
- `PROMPT_REGISTRY` dict with 5 entries: `default`, `airdrop`, `testnet`, `macro`, `defi`
- Each entry has `translate_system`, `rewrite_system`, `user_template`
- `prompt_for_tags(tags)` — selects by priority order: airdrop → testnet → macro → defi → default
- Tag-specific tone variations: airdrop (URGENT/FOMO), testnet (instructional), macro (analytical), defi (technical)
- Helper functions: `_make_airdrop_translate/rewrite()`, `_make_testnet_translate/rewrite()`, `_make_macro_translate/rewrite()`, `_make_defi_translate/rewrite()`
- Base system prompts defined as module-level constants with Vietnamese crypto style guidelines
- **Commit:** `8bc8148`

### Task 2: Implement OpenRouter API caller with fallback chain
- `OpenRouterClient(api_key, http_client)` class
- `call(model, messages, temperature, max_tokens)` — POST to `/api/v1/chat/completions`
- `call_with_fallback(system_prompt, user_content, temperature, max_tokens)` — tries models in order: `deepseek-chat:free` → `meta-llama/llama-3-70b-instruct:free` → `qwen/qwen-2.5-72b-instruct:free`
- Handles: httpx.TimeoutException, httpx.HTTPStatusError, json.JSONDecodeError — logs warning, tries next model
- `call_structured(system_prompt, user_content, response_model, temperature)` — uses `response_format: {"type": "json_object"}`, validates with `model_validate_json()`, returns `(result, used_fallback)`
- Custom `AllModelsExhausted` exception when all models fail
- `FALLBACK_MODELS` list with 3 free-tier OpenRouter models
- **Commit:** `8bc8148`

### Task 3: Implement 2-stage processing (translate → rewrite)
- `AIConsumer._process_message(msg) -> DraftContent | None`:
  1. Select prompt from registry based on `channel_tags[msg.source_channel]`
  2. Preprocess via `TextPreprocessor`
  3. **Stage 1 (Translate):** `call_structured()` with translate prompt → `TranslatedText` model (temperature 0.6)
  4. **Stage 2 (Rewrite):** `call_structured()` with rewrite prompt → `DraftContent` model (temperature 0.7)
  5. **Partial failure (D-17):** Stage 1 succeeds, Stage 2 fails → create DraftContent with translated text as body, log WARNING
  6. **Full failure (D-16):** Both stages exhaust → log ERROR, call `pause_ai()`, return None
  7. On success: set tags + status="pending" + used_fallback flag
- `TranslatedText(BaseModel)` with single `translated_text: str` field
- `pause_ai(duration=300)` — pauses all workers for N seconds when all models exhausted
- `_auto_resume()` — clears pause after cooldown
- Empty preprocessed messages skipped with log info
- **Commit:** `8bc8148`

### Task 4: Wire processing loop in AIConsumer workers
- Worker loop: checks `_shutdown.is_set()` and `_pause.is_set()` on each iteration
- Logs WARNING when raw_queue > 10 (backpressure)
- Calls `rate_limiter.acquire()` before each message
- Catches unexpected errors per worker (doesn't crash pool)
- Calls `raw_queue.task_done()` in finally block
- **Commit:** `8bc8148`

## Verification
- PROMPT_REGISTRY contains 5 entries: default, airdrop, testnet, macro, defi
- OpenRouter client with 3-model fallback chain
- 2-stage processing: translate → rewrite produces DraftContent
- Partial failure mode (translate OK, rewrite fail) handled
- Full failure mode pauses AI for 300 seconds
- `call_structured` returns `(result, used_fallback)` tuple

## Key Decisions
- 5 tag-specific prompt templates with tone variations per AI-SPEC §7.5
- 3 free-tier OpenRouter models in fallback chain (deepseek-chat, llama-3-70b, qwen-2.5-72b)
- `response_format: json_object` for structured output parsing
- Partial failure: degraded output rather than silent discard (D-17)
- Pause cooldown on all-models-exhausted (300s default)
