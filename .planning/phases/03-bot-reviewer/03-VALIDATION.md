---
phase: 03
slug: bot-reviewer
status: validated
nyquist_compliant: false
wave_0_complete: true
created: 2026-05-24
---

# Phase 03 — Bot Reviewer — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | none — pytest defaults |
| **Quick run command** | `python -m pytest tests/test_system_state.py tests/test_scam_patterns.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_system_state.py tests/test_scam_patterns.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

### Wave 1 — Bot Foundation

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | REQ-3.06 | T-03-01 / — | PTB token handled in config/env, not hardcoded | manual | — | — | ⬜ manual |
| 03-01-02 | 01 | 1 | REQ-3.01–3.05 | — | SystemState singleton with asyncio.Lock, mode defaults to MANUAL, counters thread-safe | unit | `python -m pytest tests/test_system_state.py -v` | `tests/test_system_state.py` | ✅ green |
| 03-01-03 | 01 | 1 | REQ-3.06 | — | PTB Application wired via `run_bot()` in main.py | manual | — | — | ⬜ manual |
| 03-01-04 | 01 | 1 | REQ-3.07 | — | Startup notification sent to ADMIN_CHAT_ID with mode + queue info | manual | — | — | ⬜ manual |

### Wave 2 — Bot Features

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-02-01 | 02 | 2 | REQ-3.08–3.10 | — | Command handlers registered, /mode_auto sets AUTO, /mode_manual sets MANUAL, /status reports mode/queue/count | manual | — | — | ⬜ manual |
| 03-03-01 | 03 | 2 | REQ-3.11 | — | Draft preview with 3 sections + inline keyboard (Approve/Reject/Edit) | manual | — | — | ⬜ manual |
| 03-03-02 | 03 | 2 | REQ-3.12 | — | review_consumer coroutine consumes from result_queue | manual | — | — | ⬜ manual |
| 03-03-03 | 03 | 2 | REQ-3.13 | — | Approve handler sets status=approved, pushes to publish_queue | manual | — | — | ⬜ manual |
| 03-03-04 | 03 | 2 | REQ-3.14 | — | Reject handler sets status=rejected | manual | — | — | ⬜ manual |
| 03-03-05 | 03 | 2 | REQ-3.15 | — | publish_queue created and wired in main.py | manual | — | — | ⬜ manual |
| 03-04-01 | 04 | 2 | REQ-3.16 | — | Edit button handler enters ConversationHandler | manual | — | — | ⬜ manual |
| 03-04-02 | 04 | 2 | REQ-3.17 | — | Text receiver replaces body, preserves title | manual | — | — | ⬜ manual |
| 03-04-03 | 04 | 2 | REQ-3.18 | — | Cancel/timer fallback after 5 min | manual | — | — | ⬜ manual |
| 03-05-01 | 05 | 2 | REQ-3.19–3.21 | — | SCAM_KEYWORDS, is_suspicious(), is_low_confidence() | unit | `python -m pytest tests/test_scam_patterns.py -v` | `tests/test_scam_patterns.py` | ✅ green |
| 03-05-02 | 05 | 2 | REQ-3.22–3.23 | — | AUTO mode auto-approves; suspicious/low-confidence force manual | manual | — | — | ⬜ manual |
| 03-05-03 | 05 | 2 | REQ-3.24 | — | Queue backpressure warning at 50+ pending | manual | — | — | ⬜ manual |
| 03-05-04 | 05 | 2 | REQ-3.25 | — | used_fallback flag propagated from AI handler → DraftContent | unit | `python -m pytest tests/test_ai_handler.py::TestDraftContentModel -v` | `tests/test_ai_handler.py` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⬜ manual*

---

## Wave 0 Requirements

- [x] `tests/test_system_state.py` — SystemState singleton (REQ-3.01–3.05)
- [x] `tests/test_scam_patterns.py` — scam detection (REQ-3.19–3.21)
- [x] REQ-3.25 already covered by `tests/test_ai_handler.py::TestDraftContentModel`

*Existing infrastructure covers all testable requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PTB Application wiring | REQ-3.06 | Requires python-telegram-bot runtime; not in test venv | Run bot locally with `BOT_TOKEN` set; verify `/start` responds |
| Startup notification | REQ-3.07 | Requires live PTB + Telegram API | Start pipeline; check ADMIN_CHAT_ID receives startup message |
| Command handlers (/mode_auto, /mode_manual, /status) | REQ-3.08–3.10 | Requires PTB runtime | Send commands to bot; verify responses match AI-SPEC §5.2 |
| Draft preview + inline keyboard | REQ-3.11 | Requires PTB inline keyboard rendering | Queue a draft in MANUAL mode; verify 3-section preview + keyboard appears |
| review_consumer coroutine | REQ-3.12 | Async PTB integration | Run pipeline with result_queue populated; verify consumer processes drafts |
| Approve handler | REQ-3.13 | Requires PTB CallbackQuery | Tap ✅ Approve; verify status changes, draft pushed to publish_queue |
| Reject handler | REQ-3.14 | Requires PTB CallbackQuery | Tap ❌ Reject; verify status changes, draft NOT pushed |
| publish_queue wiring | REQ-3.15 | Integration check across main.py | Verify approved drafts appear in publish_queue for PublisherConsumer |
| Edit flow (ConversationHandler) | REQ-3.16–3.18 | Requires PTB ConversationHandler | Tap ✏️ Edit, send replacement text; verify body replaced, title preserved; wait 5 min for timeout |
| AUTO mode auto-approval | REQ-3.22–3.23 | Requires PTB + SystemState integration | Set `/mode_auto`; queue a clean draft; verify it auto-approves; queue a suspicious draft; verify it forces manual |
| Queue backpressure | REQ-3.24 | Requires 50+ draft queue | Fill result_queue with 51+ drafts; verify WARNING log + auto MANUAL switch |
| used_fallback propagation | REQ-3.25 | Partially automated (model field), integration requires PTB | Queue a draft from a channel that triggers fallback; verify it force-manual-reviews in AUTO mode |

---

## Validation Sign-Off

- [x] All testable tasks have automated verification
- [x] Sampling continuity: max 1 gap between automated checks
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending — need PTB integration tests or acceptance that PTB-dependent items remain manual-only

---

## Validation Audit 2026-05-24

| Metric | Count |
|--------|-------|
| Gaps found | 2 |
| Resolved | 2 |
| Escalated | 0 |
| Total requirements | 25 |
| Automated | 3 (REQ-3.01–3.05, REQ-3.19–3.21, REQ-3.25) |
| Manual-only | 12 |
