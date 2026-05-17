# Phase 3: Bot Reviewer & Mode Management - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Consume `DraftContent` objects from the result queue, send to admin for review via Telegram Bot with inline keyboard (Approve/Reject/Edit), manage SYSTEM_MODE (AUTO/MANUAL) runtime switching via commands, and produce approved drafts ready for the publisher (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Bot Framework
- **D-01:** Use `python-telegram-bot` (PTB) for bot functionality — richer bot API support (InlineKeyboardMarkup, CommandHandler, ConversationHandler, filters) vs reusing Telethon

### System Mode & State Management
- **D-02:** `SYSTEM_MODE` is a singleton with `asyncio.Lock` for thread-safe runtime switching. Exposed via a `SystemState` class shared between modules through dependency injection (no global variable)
- **D-03:** Reset to `MANUAL` on every startup — safe default. Mode is not persisted across restarts
- **D-04:** Startup notification sent to `ADMIN_CHAT_ID`: "✅ Bot started | SYSTEM_MODE: MANUAL | {N} drafts in queue"

### Mode Switching Commands
- **D-05:** PTB `CommandHandler` for `/mode_auto`, `/mode_manual`, `/status`. AI-SPEC §5.2 defines the command responses verbatim
- **D-06:** `/status` reports: current mode, queue depth, drafts processed today

### Approval Flow (MANUAL Mode)
- **D-07:** Draft display — full preview with 3 sections sent as a single message:
  1. **Title** — bold, first line
  2. **Telegram preview** — in a code block
  3. **Binance Square preview** — in a separate code block
  - Inline keyboard below: `[✅ Approve] [❌ Reject] [✏️ Edit]`
- **D-08:** Approve → change `DraftContent.status` to `"approved"`, push to publish queue for Phase 4
- **D-09:** Reject → change `DraftContent.status` to `"rejected"`, log reason (optional), discard

### Edit Flow
- **D-10:** Reply-to flow — admin clicks "Edit" → bot replies asking for replacement text → admin replies with new content → bot updates draft and re-sends for re-approval
- **D-11:** The replacement text replaces the entire draft body (Telegram + Binance Square format). Title is preserved from original unless edited separately

### AUTO Mode Behavior
- **D-12:** In AUTO mode, drafts with `status="pending"` go directly to the publish queue without admin review
- **D-13:** Forced manual review exceptions (even in AUTO mode):
  a. **Scam keyword match** — flagged by scam detection patterns (AI-SPEC §9)
  b. **Low-confidence AI output** — if the AI response is malformed, very short (<100 chars), or the JSON validation required fallback, force admin review
- **D-14:** Low-confidence heuristic: if `call_structured` required a fallback model (not primary), flag as low-confidence. If draft has fewer than 3 sentences, flag as low-confidence

### Queue & Backpressure
- **D-15:** Pipeline queue (`asyncio.Queue[DraftContent]`) for approved drafts → consumed by Phase 4 publisher. Same async pattern as Phase 1→Phase 2
- **D-16:** Admin review queue is the bot's pending drafts — no separate queue. PTB handles message dispatch
- **D-17:** When pending review count exceeds 50: log WARNING, keep accepting. Same approach as AI handler backpressure (D-13 from Phase 2)

### the agent's Discretion
- Exact PTB client configuration (polling vs webhook, timeout settings)
- Draft message formatting details (field order, markdown styling within the code blocks)
- Reply-to edit flow implementation (duration timeout for edit reply, cancellation mechanism)
- Low-confidence heuristic thresholds (exact min char count, what qualifies as "very short")
- Startup message format and content details
- `/status` command output format

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### System Architecture
- `AI-SPEC.md` §3 — Data flow architecture (ingestion → processing → distribution)
- `AI-SPEC.md` §4 — Module structure, `bot_reviewer.py` responsibility
- `AI-SPEC.md` §5 — Human-in-the-Loop review mechanism & mode management (FULL — this is the primary spec for Phase 3)
- `AI-SPEC.md` §9 — Guardrails: scam detection patterns, duplicate detection

### Data Models & Integration
- `src/models.py` — `DraftContent` (status, tags, content fields), `RawMessage`
- `src/config.py` — `SYSTEM_MODE`, `TELEGRAM_BOT_TOKEN`, `ADMIN_CHAT_ID` config keys
- `AI-SPEC.md` §5.2 — Mode switching commands and responses
- `AI-SPEC.md` §5.3 — Approval flow and inline keyboard design
- `AI-SPEC.md` §5.4 — Queue management

### Prior Phase Contracts
- `.planning/phases/02-ai-handler/02-CONTEXT.md` — Phase 2 decisions (DraftContent schema, result_queue handoff)
- `src/ai_handler.py` — AIConsumer produces DraftContent objects for the result queue
- `src/main.py` — Entry point wiring; must be extended with bot reviewer consumer
- `.planning/phases/01-configuration-crawler/01-CONTEXT.md` — Phase 1 decisions (source channel config, tags)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config.py` `Config` class — Already has `bot_token`, `admin_chat_id`, `system_mode` fields configured and validated on startup
- `src/models.py` `DraftContent` — Has `status` field with `pending/approved/rejected/published` literals, `tags`, and content fields ready for review flow
- `src/main.py` — Has `result_queue: asyncio.Queue[DraftContent]` ready for bot reviewer consumption
- `src/logging_setup.py` — Structured logging config reusable by new module

### Established Patterns
- Pydantic v2 `BaseModel` for all data models
- Async/await throughout with asyncio
- Module-per-responsibility pattern in `src/`
- Pipeline queue pattern (producer → queue → consumer) established across Phase 1→2→3

### Integration Points
- `result_queue: asyncio.Queue[DraftContent]` in `main.py` — AI handler puts, bot reviewer gets
- `src/main.py` — Must create bot reviewer and register consumer alongside crawler + AI handler
- `src/config.py` — No config changes needed (all required keys already present)
- `src/models.py` — `DraftContent.status` literals already include all needed states

</code_context>

<specifics>
## Specific Ideas

- Inline keyboard with 3 buttons (Approve/Reject/Edit) per AI-SPEC §5.3
- PTB ConversationHandler for the reply-to edit flow
- Startup message as status indicator — admin knows system is alive without checking

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-bot-reviewer*
*Context gathered: 2026-05-17*
