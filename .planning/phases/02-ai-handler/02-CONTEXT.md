# Phase 2: AI Handler & Processing - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Consume `RawMessage` objects from the crawler queue, preprocess raw text, call OpenRouter AI for two-stage processing (translate → rewrite to Vietnamese), validate structured JSON output, and produce `DraftContent` objects for the distribution layer (Phases 3-4).

</domain>

<decisions>
## Implementation Decisions

### Text Preprocessing
- **D-01:** URLs kept in text — AI decides to keep or remove based on context during rewrite
- **D-02:** Emojis stripped from input — AI adds appropriate emojis during rewrite stage
- **D-03:** Code blocks, contract addresses, and wallet addresses preserved verbatim — AI must not modify these
- **D-04:** Minimum text length already enforced by Phase 1 (50 chars) — no additional length filter needed

### AI Call Architecture
- **D-05:** Two-stage pipeline — Stage 1: translate to Vietnamese. Stage 2: rewrite in crypto-VN community style. Two separate API calls per message
- **D-06:** Temperature 0.5-0.7 for both stages (balanced between accuracy and creativity)
- **D-07:** Maximum 2048 tokens per stage
- **D-08:** Tag-specific system prompts — different prompts depending on source channel tags (airdrop, testnet, macro, etc.). The system prompt registry maps tags → prompts
- **D-09:** System prompts follow AI-SPEC §7.5 as base template, with tag-specific variations
- **D-10:** Fallback chain per AI-SPEC §6.2: deepseek-chat:free → llama-3-70b-instruct:free → qwen-2.5-72b-instruct:free

### Consumer Concurrency & Rate Limiting
- **D-11:** Small worker pool — 2-3 concurrent AI calls processing messages simultaneously
- **D-12:** Global rate limiter (token bucket) — proactive limiting, not just reactive backoff. Prevents hitting OpenRouter free tier rate limits
- **D-13:** Backpressure — log warning when queue grows, keep processing. No crawler pausing in v1

### DraftContent Model
- **D-14:** Fields: `title_vn`, `telegram_markdown`, `binance_square_markdown`, `status` (pending/approved/rejected/published, default=pending), `tags` (list[str] from source channel)
- **D-15:** Source attribution (original_channel, message_id) stays in `RawMessage` — not duplicated into `DraftContent`

### Failed Message Handling
- **D-16:** All models exhausted → skip message, log ERROR, continue processing next message (do not pause pipeline, no dead-letter queue in v1)
- **D-17:** Partial failure (translate succeeds, rewrite fails) → use translated text as draft content, log WARNING, push to queue

### the agent's Discretion
- Exact rate limiter implementation (token bucket parameters — initial tokens, refill rate)
- Dead-letter queue implementation deferred — if needed, add in a future phase
- Prompt template format and exact wording per tag type (follows AI-SPEC §7.5 base)
- Worker pool implementation details (asyncio.Queue for workers, worker lifecycle)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### System Architecture
- `AI-SPEC.md` §3 — Data flow architecture (ingestion → processing → distribution)
- `AI-SPEC.md` §4 — Module structure, `ai_handler.py` responsibility, `DraftContent` model reference
- `AI-SPEC.md` §6.2 — OpenRouter fallback chain (model priority, retry logic)
- `AI-SPEC.md` §6.3 — Structured outputs validation (response_format, DraftContent schema)
- `AI-SPEC.md` §7 — Content standards: terminology, tone, output format, prompt engineering
- `AI-SPEC.md` §7.5 — Base system prompt for translation + rewrite
- `AI-SPEC.md` §9 — Guardrails: content length check, duplicate detection, scam detection

### Integration with Phase 1
- `.planning/phases/01-configuration-crawler/01-CONTEXT.md` — Phase 1 decisions (RawMessage contract, source tags)
- `src/models.py` — Current models (RawMessage, SourceConfig); DraftContent will be added here
- `src/crawler.py` — Consumer architecture (asyncio.Queue, message flow)
- `src/main.py` — Entry point wiring; must be extended with AI handler consumer

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/crawler.py` `TelegramCrawler` — Producer pattern (put on asyncio.Queue). AI handler will be consumer (get from same queue)
- `src/models.py` `RawMessage` — Input type for AI handler. `RawMessage.raw_text` is the content to process
- `src/models.py` `SourceConfig` — Contains `tags` list that will be used for tag-specific prompt selection
- `src/logging_setup.py` — Logging config with structured format (reused by new module)

### Established Patterns
- Pydantic v2 `BaseModel` for all data models
- Async/await throughout with asyncio
- Module-per-responsibility pattern in `src/`
- Exponential backoff for API resilience (established in Phase 1)

### Integration Points
- `asyncio.Queue[RawMessage]` in `main.py` — Crawler puts, AI handler gets
- `src/models.py` — Add `DraftContent` model (extends existing models)
- `src/main.py` — Must create AI handler, register consumer tasks alongside crawler
- `src/config.py` — May need config for AI-specific settings (rate limits, model preferences)

</code_context>

<specifics>
## Specific Ideas

- Two-stage processing (translate → rewrite) for better quality control compared to single-pass
- Tag-specific prompts so airdrop news gets urgency/FOMO tone while macro analysis gets informative tone
- Use translated text as fallback when rewrite fails — graceful degradation rather than losing messages

</specifics>

<deferred>
## Deferred Ideas

- Dead-letter queue for persistently failing messages — future phase
- Crawler auto-pause on deep queue — v2 enhancement
- Configurable language/style (not just Vietnamese) — future enhancement

</deferred>

---

*Phase: 02-ai-handler*
*Context gathered: 2026-05-17*
