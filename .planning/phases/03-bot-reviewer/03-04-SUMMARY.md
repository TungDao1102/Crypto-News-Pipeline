# Plan 03-04 — Edit Flow (Reply-to) — Summary

## Objective
Implement reply-to edit flow using PTB ConversationHandler.

## Tasks Completed

### Task 1: Edit button handler (entry point)
- `handle_edit()` — parses `draft_index` from callback data
- Replies asking for replacement text, transitions to `WAITING_EDIT_TEXT` state
- Stores `edit_draft_index` in `context.user_data`
- **Commit:** `3409f1b`

### Task 2: Text receiver handler
- `receive_edit()` — receives admin's reply text
- Replaces both `telegram_markdown` and `binance_square_markdown` with new content
- Title preserved from original draft
- Re-sends updated draft for re-approval with fresh inline keyboard
- Logs: `Draft {index} edited by admin`
- **Commit:** `3409f1b`

### Task 3: Cancel/timer fallback
- Conversation timeout after 300 seconds (5 minutes) → notifies admin: "⏰ Edit timed out. Draft preserved as-is."
- `/cancel` command handler → "✖️ Edit cancelled. Draft preserved as-is."
- `edit_timeout()` callback handler for timed-out callback queries
- **Commit:** `3409f1b`

## Verification
- ConversationHandler registered with entry_points, states, fallbacks, and conversation_timeout
- WAITING_EDIT_TEXT state (value 1) with MessageHandler for TEXT & ~COMMAND
- Fallbacks: /cancel CommandHandler + edit_timeout CallbackQueryHandler
- Draft preserved on timeout/cancel (no data loss)
- Python syntax valid

## Key Decisions
- Reply-to flow using PTB ConversationHandler (D-10 from CONTEXT.md)
- Replacement text replaces both body fields, title preserved (D-11)
- 5-minute timeout window for edit response
- Draft preserved as-is on timeout/cancel
