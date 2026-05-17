# Phase 3: Bot Reviewer & Mode Management — Execution Plan

**Status:** Planned
**Waves:** 2
**Plans:** 5

---

## Wave 1 — Bot Foundation

### Plan 01: Bot Setup & System State

**Objective:** Set up python-telegram-bot application, create SystemState singleton, wire into main.py, send startup notification.

**Files to modify:**
- `requirements.txt` — add python-telegram-bot>=21.0,<22
- `src/system_state.py` — NEW: SystemState singleton with asyncio.Lock
- `src/main.py` — wire up PTB Application and bot reviewer

**Tasks:**

1. **Add dependency**
   - Add `python-telegram-bot>=21.0,<22` to requirements.txt

2. **Create SystemState**
   - `src/system_state.py`:
   - Singleton pattern with `asyncio.Lock`
   - `mode: Literal["AUTO", "MANUAL"]` — defaults to `"MANUAL"`
   - `drafts_processed_today: int` counter
   - `async def set_mode(mode) -> None` — thread-safe via lock
   - `async def get_mode() -> str`
   - `async def increment_processed() -> None`
   - Mode resets to MANUAL on every startup (no persistence)

3. **Wire PTB Application in main.py**
   - Initialize `Application.builder().token(config.bot_token).build()`
   - Add `SystemState` to `context.bot_data` for cross-module access
   - Run PTB in polling mode alongside existing asyncio tasks

4. **Startup notification**
   - On bot start, send to `ADMIN_CHAT_ID`:
     `✅ Bot started | SYSTEM_MODE: MANUAL | {N} drafts in queue`

---

## Wave 2 — Bot Features (depends on Wave 1)

### Plan 02: Command Handlers

**Objective:** Implement `/mode_auto`, `/mode_manual`, `/status` commands.

**Files to modify:**
- `src/bot_reviewer.py` — NEW: PTB command handlers

**Tasks:**

1. **Create bot_reviewer.py with CommandHandler registration**
   - `register_handlers(application, system_state, result_queue)` — registers all handlers on the PTB Application

2. **`/mode_auto` handler**
   - Call `system_state.set_mode("AUTO")`
   - Reply: `✅ Chế độ AUTO — Bài viết sẽ được đăng tự động.`

3. **`/mode_manual` handler**
   - Call `system_state.set_mode("MANUAL")`
   - Reply: `👤 Chế độ MANUAL — Bài viết chờ Admin duyệt.`

4. **`/status` handler**
   - Report: current mode, queue depth (from `result_queue.qsize()`), drafts processed today
   - Format:
     ```
     📊 **System Status**
     Mode: {AUTO/MANUAL}
     Queue: {N} drafts pending
     Processed today: {N}
     ```

### Plan 03: Approval Flow (MANUAL Mode)

**Objective:** Consume DraftContent from result_queue, send full preview to admin with inline keyboard (Approve/Reject/Edit).

**Files to modify:**
- `src/bot_reviewer.py` — add preview sending, callback handlers, publish_queue
- `src/main.py` — create publish_queue, pass to reviewer

**Tasks:**

1. **Draft display format**
   - Single message with 3 sections:
     ```
     📝 **{title_vn}**
     
     \`\`\`
     {telegram_markdown}
     \`\`\`
     
     \`\`\`
     {binance_square_markdown}
     \`\`\`
     ```
   - Inline keyboard below: `[✅ Approve] [❌ Reject] [✏️ Edit]`
   - Callback data: `approve:{draft_index}`, `reject:{draft_index}`, `edit:{draft_index}`

2. **Draft consumer coroutine**
   - `async def review_consumer(result_queue, publish_queue, system_state, application, admin_chat_id)`
   - Loop: get DraftContent from result_queue → send to admin
   - Track pending drafts in a dict `{draft_index: DraftContent}`

3. **Approve handler (CallbackQuery)**
   - Parse `draft_index` from callback data
   - Set `draft.status = "approved"`
   - Push to `publish_queue`
   - Edit original message to show ✅ Approved
   - Log: `[reviewer] ✅ draft_{index} approved by admin`

4. **Reject handler (CallbackQuery)**
   - Parse `draft_index`
   - Set `draft.status = "rejected"`
   - Edit original message to show ❌ Rejected
   - Log: `[reviewer] ❌ draft_{index} rejected by admin`

5. **Wire publish_queue in main.py**
   - Create `publish_queue: asyncio.Queue[DraftContent] = asyncio.Queue()`
   - Pass to `register_handlers()` and `review_consumer()`

### Plan 04: Edit Flow (Reply-to)

**Objective:** Implement reply-to edit flow using PTB ConversationHandler.

**Files to modify:**
- `src/bot_reviewer.py` — add ConversationHandler for edit flow

**Tasks:**

1. **Edit button handler (entry point)**
   - Parse `draft_index` from callback data
   - Reply to the draft message asking for replacement text
   - Transition to `WAITING_EDIT_TEXT` state
   - Store `{chat_id: draft_index}` in context.user_data

2. **Text receiver handler**
   - Receive admin's reply with new content
   - Replace the entire draft body (telegram_markdown + binance_square_markdown) with the new text
   - Title preserved from original
   - Re-send the updated draft for re-approval with fresh inline keyboard
   - Log: `[reviewer] ✏️ draft_{index} edited by admin`

3. **Cancel/timer fallback**
   - Timeout after 5 minutes waiting for edit text → cancel edit
   - Notify admin: `⏰ Edit timed out. Draft preserved as-is.`

### Plan 05: AUTO Mode & Guardrails

**Objective:** Implement AUTO mode auto-approval, scam detection, low-confidence heuristics, queue backpressure warning.

**Files to modify:**
- `src/bot_reviewer.py` — add AUTO mode logic and guardrails
- `src/scam_patterns.py` — NEW: scam keyword patterns

**Tasks:**

1. **Scam detection patterns**
   - `src/scam_patterns.py`:
   - `SCAM_KEYWORDS` list: pump, dump, get-rich-quick, guaranteed, double your, risk-free, etc.
   - `def is_suspicious(text: str) -> bool` — case-insensitive keyword match
   - `def is_low_confidence(draft: DraftContent, used_fallback: bool) -> bool` — heuristic: <100 chars or <3 sentences or used fallback model

2. **AUTO mode consumer logic**
   - When `system_state.get_mode() == "AUTO"`:
     - Check `is_suspicious()` — if True → force manual review (send to admin)
     - Check `is_low_confidence()` — if True → force manual review
     - Otherwise: auto-set status to "approved", push to publish_queue
   - Log: `[reviewer] 🤖 AUTO approved draft_{index}`

3. **Queue backpressure**
   - When pending review count > 50: log WARNING, keep accepting
   - Format: `[reviewer] ⚠️ Review queue at {N} pending — backpressure warning`

4. **Integration**
   - Pass `used_fallback` flag from AIConsumer to DraftContent (or as separate signal)
   - Wire scam detection into both AUTO and MANUAL flows
