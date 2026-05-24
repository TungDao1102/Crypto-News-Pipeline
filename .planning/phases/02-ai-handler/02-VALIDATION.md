---
phase: 02
slug: ai-handler
status: validated
nyquist_compliant: false
created: 2026-05-24
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| **Config file** | none — tests run from project root |
| **Quick run command** | `python -m pytest tests/test_ai_handler.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_ai_handler.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test File | Status |
|---------|------|------|-------------|-----------|--------|
| 02-01-01 | 01 | 1 | D-14 | `model imports verify` | ✅ green |
| 02-01-02 | 01 | 1 | D-15 | `TestDraftContentModel` | ✅ green |
| 02-02-01 | 02 | 1 | D-01 | `TestTextPreprocessor` | ✅ green |
| 02-02-02 | 02 | 1 | D-02, D-03 | `TestTokenBucket` | ✅ green |
| 02-02-03 | 02 | 1 | D-04, D-11, D-12 | `TestAIConsumer::test_shutdown_cancels_workers` | ✅ green |
| 02-03-01 | 03 | 2 | D-05, D-06 | `TestPromptRegistry`, `TestPromptForTags` | ✅ green |
| 02-03-02 | 03 | 2 | D-07, D-08, D-09 | `TestOpenRouterClient` | ✅ green |
| 02-03-03 | 03 | 2 | D-10, D-13, D-16, D-17 | `TestAIConsumer::test_process_message_*` | ✅ green |
| 02-03-04 | 03 | 2 | D-13 | `test_pause_*`, `test_worker_*` (existing) | ✅ green |
| 02-04-01 | 04 | 2 | D-05 | `TestAIConsumer::test_channel_tags_lookup` | ✅ green |
| 02-04-02 | 04 | 2 | D-06, D-07, D-08, D-09, D-10 | `TestAIConsumer::test_process_message_full_success` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `OpenRouterClient.call()` real HTTP integration | D-08 | Requires live API key | Run with valid `.env`: `python -c "from src.ai_handler import OpenRouterClient; import httpx; c=OpenRouterClient('key', httpx.AsyncClient()); await c.call('deepseek-chat:free', [{'role':'user','content':'hi'}])"` |
| `main.py` full startup with both crawler + AI consumer | D-05..D-10 | Requires live Telegram API + OpenRouter key | `python src/main.py` with valid `.env`, verify both tasks start via logs |
| Graceful shutdown on SIGINT/SIGTERM | D-10 | Requires process signals | Start `python src/main.py`, press Ctrl+C within 2s, verify clean shutdown logs |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none needed)
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
