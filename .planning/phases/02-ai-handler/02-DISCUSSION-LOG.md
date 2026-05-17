# Phase 2: AI Handler & Processing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 02-ai-handler
**Areas discussed:** Text Preprocessing, AI Call Architecture, Consumer Concurrency & Rate Limiting, DraftContent Model Fields, Failed Message Handling

---

## Text Preprocessing

| Option | Description | Selected |
|--------|-------------|----------|
| Strip all URLs | Remove all URLs before AI processing | |
| Keep but rewrite | Keep URLs, AI decides to keep or remove based on context | ✓ |
| Strip suspicious, keep known | Strip unknown domains, keep crypto-known domains | |

**User's choice:** Keep but rewrite
**Notes:** URLs are domain-specific context — AI can judge relevance better than a static rule.

| Option | Description | Selected |
|--------|-------------|----------|
| Raw input — AI handles | Send raw text with emoji, markdown, special chars | |
| Strip emoji — AI rewrites | Strip emoji before AI, let AI add appropriate ones | ✓ |

**User's choice:** Strip emoji — AI rewrites
**Notes:** Original emojis are source-specific and may not fit Vietnamese style. AI generates better emojis for target audience.

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve verbatim | Keep code blocks, contract addresses, wallet addresses untouched | ✓ |
| AI handles freely | Let AI decide | |

**User's choice:** Preserve verbatim
**Notes:** Crypto addresses must not be modified — accuracy is critical.

---

## AI Call Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Single prompt | One call: translate + rewrite together | |
| 2-stage | Stage 1 translate, Stage 2 rewrite | ✓ |

**User's choice:** 2-stage
**Notes:** Better quality control at cost of 2x API calls. Each stage has dedicated prompt.

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative (0.3-0.5) | Low temperature, precise but less creative | |
| Balanced (0.5-0.7) | Balanced accuracy and creativity | ✓ |
| Allow high (0.7-0.9) | Creative but risk hallucination | |

**User's choice:** Balanced (0.5-0.7)
**Notes:** AI-SPEC default of 0.7 is within this range. Same temperature for both stages.

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed prompt, 1024 tokens | One prompt for all tags, shorter limit | |
| Fixed prompt, 2048 tokens | One prompt, longer limit (AI-SPEC default) | |
| Tag-specific prompts | Different prompts per tag type, 2048 tokens | ✓ |

**User's choice:** Tag-specific prompts
**Notes:** Airdrop, testnet, macro each get tailored prompts. Token limit: 2048 per stage.

---

## Consumer Concurrency & Rate Limiting

| Option | Description | Selected |
|--------|-------------|----------|
| 1 consumer (sequential) | One message at a time | |
| Small pool (2-3 workers) | 2-3 concurrent AI calls | ✓ |
| Aggressive (5-10 workers) | High concurrency, risk rate limits | |

**User's choice:** Small pool (2-3 workers)
**Notes:** Two-stage means 4-6 API calls per message in flight. Good balance.

| Option | Description | Selected |
|--------|-------------|----------|
| Backoff per worker | Each worker handles 429 independently | |
| Global rate limiter | Token bucket before all workers | ✓ |
| No special handling | Just fallback chain | |

**User's choice:** Global rate limiter
**Notes:** Proactive control prevents hitting free tier rate limits. Token bucket implementation deferred to agent's discretion.

| Option | Description | Selected |
|--------|-------------|----------|
| Log warning, keep processing | Queue builds up, log depth | ✓ |
| Pause crawler temporarily | Stop crawler when queue exceeds threshold | |

**User's choice:** Log warning, keep processing
**Notes:** In practice crawler produces slowly (event-driven, real-time) so queue growth is unlikely.

---

## DraftContent Model Fields

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add source fields | Include original_channel, message_id, link | |
| No — source in RawMessage | Keep source attribution in RawMessage only | ✓ |

**User's choice:** No — source in RawMessage
**Notes:** RawMessage already has source_channel and message_id. DraftContent is pure processed content.

| Option | Description | Selected |
|--------|-------------|----------|
| No status field | Phase 3 manages status | |
| Add status field | Include status pending/approved/rejected/published | ✓ |

**User's choice:** Add status field
**Notes:** Default: "pending". Bot Reviewer (Phase 3) transitions status. Makes DraftContent self-contained.

| Option | Description | Selected |
|--------|-------------|----------|
| Add tags field | Copy tags from SourceConfig | ✓ |
| No — inferred from content | Publisher handles tags based on content | |

**User's choice:** Add tags field
**Notes:** Tags from source channel carried forward. Publisher (Phase 4) uses tags for hashtag/cashtag selection.

---

## Failed Message Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Skip and log | Discard message, log ERROR, continue | ✓ |
| Dead-letter queue | Defer to retry/retry queue | |
| Pause pipeline | Stop processing for 5 minutes | |

**User's choice:** Skip and log
**Notes:** No pipeline pause. Fallback chain already provides resilience — if all 3 models fail, message is likely problematic.

| Option | Description | Selected |
|--------|-------------|----------|
| Use translated text as draft | Partial result better than nothing | ✓ |
| Skip entirely | Both stages must succeed | |

**User's choice:** Use translated text as draft
**Notes:** Graceful degradation. If translate works but rewrite fails, push translated text with WARNING log.

---

## the agent's Discretion

1. Token bucket implementation details (initial tokens, refill rate)
2. Worker pool implementation (worker lifecycle, task management)
3. Dead-letter queue — explicitly deferred; implement if user later requests
4. Prompt template format per tag type (base from AI-SPEC §7.5)

## Deferred Ideas

- Dead-letter queue for persistently failing messages — future phase
- Crawler auto-pause on deep queue — v2 enhancement
- Configurable language/style (not just Vietnamese) — future enhancement
