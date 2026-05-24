# Plan 03-03 — Approval Flow (MANUAL Mode) — Summary

## Objective
Consume DraftContent from result_queue, send full preview to admin with inline keyboard (Approve/Reject), wire publish_queue in main.py.

## Tasks Completed

### Task 1: Draft display format
- Single message with 3 sections: title (bold), telegram_markdown in code block, binance_square_markdown in code block
- Inline keyboard below: `[✅ Approve] [❌ Reject] [✏️ Edit]`
- Callback data format: `approve:{draft_index}`, `reject:{draft_index}`, `edit:{draft_index}`
- Helper functions: `_build_draft_text()` and `_build_keyboard()`
- **Commit:** `3409f1b`

### Task 2: Draft consumer coroutine
- `async def review_consumer(result_queue, application, admin_chat_id)` 
- Loop: gets DraftContent from result_queue, sends to admin with inline keyboard
- Tracks pending drafts in `_pending_drafts: dict[int, DraftContent]`
- Global `_next_index` counter for draft tracking
- Backpressure warning when >50 pending drafts
- **Commit:** `3409f1b`

### Task 3: Approve handler (CallbackQuery)
- Parses `draft_index` from callback data
- Sets `draft.status = "approved"`, pushes to `publish_queue`
- Increments `system_state.drafts_processed_today`
- Edits original message to show ✅ Approved
- Logs: `Draft {index} approved by admin`
- **Commit:** `3409f1b`

### Task 4: Reject handler (CallbackQuery)
- Parses `draft_index` from callback data
- Sets `draft.status = "rejected"`
- Edits original message to show ❌ Rejected
- Logs: `Draft {index} rejected by admin`
- **Commit:** `3409f1b`

### Task 5: Wire publish_queue in main.py
- `publish_queue: BoundedQueue[DraftContent]` created alongside `raw_queue` and `result_queue`
- Passed to `run_bot()` and stored in `application.bot_data["publish_queue"]`
- `review_consumer` reads from it after approval
- **Commit:** `3409f1b`

## Verification
- Draft preview format: 3 sections + inline keyboard verified in code
- Approve flow: callback handler reads draft index, sets status, pushes to publish_queue
- Reject flow: callback handler reads draft index, sets status, edits message
- _pending_drafts properly cleaned up on approve/reject
- publish_queue created in main.py and wired through to bot_reviewer

## Key Decisions
- Inline keyboard with 3 buttons (Approve/Reject/Edit) per AI-SPEC §5.3
- Pending drafts stored in module-level dict (in-memory, no persistence needed)
- asyncio.Queue pattern for publish_queue (same as Phase 1→2 queues)
