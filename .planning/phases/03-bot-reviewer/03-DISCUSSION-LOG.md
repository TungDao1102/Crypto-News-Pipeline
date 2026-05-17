# Phase 3: Bot Reviewer & Mode Management - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 03-bot-reviewer
**Areas discussed:** Bot framework, Edit flow, AUTO overrides, Publisher handoff, Draft display, Mode persistence, Startup notification, Queue backpressure

---

## Bot Framework

| Option | Description | Selected |
|--------|-------------|----------|
| python-telegram-bot (PTB) | Rich bot features: InlineKeyboardMarkup, CommandHandler, ConversationHandler, filters. New dependency but purpose-built for bots. | ✓ |
| Telethon Bot API | Reuse existing Telethon dependency. @bot.on(events.CallbackQuery) for inline keyboards. Fewer built-in handlers but avoids adding a new package. | |
| No preference | Use whatever makes more sense technically | |

**User's choice:** python-telegram-bot (PTB)
**Notes:** User wants the richer bot-specific features that PTB provides

---

## Edit Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Reply-to flow | Bot replies to the inline keyboard message asking for replacement text. Admin replies with new text. | ✓ |
| Inline edit mode | Bot enters an edit session — admin sends messages incrementally, clicks Done to finish. | |
| Separate edit command | Admin uses /edit {draft_id} — structured field-by-field editing. | |

**User's choice:** Reply-to flow
**Notes:** Simple, familiar Telegram pattern

---

## AUTO Overrides

| Option | Description | Selected |
|--------|-------------|----------|
| Scam detection only | Only scam-keyword matches bypass AUTO. Simplest path. | |
| Scam + first N messages | First 3-5 messages each day go through manual review. | |
| Scam + low-confidence AI output | Low-confidence AI output forces manual review alongside scam detection. | ✓ |

**User's choice:** Scam + low-confidence AI output
**Notes:** Quality gate even in AUTO mode

---

## Publisher Handoff

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline queue (same approach) | Approved DraftContent goes to publish_queue. Phase 4 consumes. | ✓ |
| Database table | Write approved drafts to SQLite. Crash recovery. | |
| File-based queue | JSON-line file queue. Minimal persistence. | |

**User's choice:** Pipeline queue (same queue approach)
**Notes:** Consistent with Phase 1→2 async queue pattern

---

## Draft Display

| Option | Description | Selected |
|--------|-------------|----------|
| Full preview — 3 sections | Title, Telegram preview in code block, Binance Square preview in code block. | ✓ |
| Summary with expand | Compact summary card. Admin expands to see full content. | |
| Telegram preview only | Show Telegram format as main preview. Binance Square as secondary. | |

**User's choice:** Full preview — 3 sections
**Notes:** Admin sees exactly what will be published

---

## Mode Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Reset to MANUAL every startup | Always start in MANUAL. Safe default. | ✓ |
| Persist last-used mode | Save to .system_mode file. Resume in same mode. | |

**User's choice:** Reset to MANUAL every startup
**Notes:** Safety-first approach

---

## Startup Notification

| Option | Description | Selected |
|--------|-------------|----------|
| Send startup message | Bot notifies admin on startup with mode and queue info. | ✓ |
| Silent startup | No startup notification. | |

**User's choice:** Send startup message
**Notes:** Helps admin know system is alive

---

## Queue Backpressure

| Option | Description | Selected |
|--------|-------------|----------|
| Warn and keep accepting | Log warning at threshold. Keep accepting drafts. | ✓ |
| Auto-pause ingestion | Auto-switch to MANUAL and pause AI processing. | |
| Auto-approve old drafts | Auto-approve drafts older than time limit. | |

**User's choice:** Warn and keep accepting (like Phase 2)
**Notes:** Consistent with Phase 2 approach

---

## the agent's Discretion

- Exact PTB client configuration (polling vs webhook, timeout settings)
- Draft message formatting details
- Reply-to edit flow implementation details
- Low-confidence heuristic thresholds
- Startup message format
- /status command output format

## Deferred Ideas

None — discussion stayed within phase scope.
