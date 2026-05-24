---
phase: 01
slug: configuration-crawler
status: validated
nyquist_compliant: false
created: 2026-05-24
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| **Config file** | none — tests run from project root |
| **Quick run command** | `python -m pytest tests/test_phase1.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_phase1.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~2 seconds

---

## Per-Task Verification Map

| Task ID | Layer | Requirement | Test | Status |
|---------|-------|-------------|------|--------|
| 01-0.1 | 0 — Scaffold | Package init | `import src` verified by all tests | ✅ green |
| 01-0.2 | 0 — Dependencies | requirements.txt | `TestDraftContentModel` (Phase 2, uses httpx) | ✅ green |
| 01-0.3 | 0 — Sources config | sources.default.json | `TestLoadSources` | ✅ green |
| 01-1.1 | 1 — Models | SourceConfig, RawMessage, ConfigError | `TestSourceConfig`, `TestRawMessage`, `TestConfigError` | ✅ green |
| 01-1.2 | 1 — Config validation | Config load + validate + warn defaults | `TestValidate`, `TestWarnDefaults`, `TestBotTokenPattern`, `TestLoadConfig` | ✅ green |
| 01-1.3 | 1 — Logging setup | setup_logging | `TestSetupLogging` | ✅ green |
| 01-2.1 | 2 — Crawler | _on_message, scam filter, rate limit, dedup | `TestCrawlerTextSimilarity`, `TestScamPatterns`, `TestCrawlerOnMessage`, `TestScamPatternRegexEdgeCases` | ✅ green |
| 01-3.1 | 3 — Main entry | main.py wiring | `TestLoadConfig::test_loads_successfully` (indirect) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Crawler connects to Telegram via Telethon | 2.1 — start() | Requires live Telegram session + API credentials | Run with valid `.env`: `python src/main.py`, verify "Crawler started" log |
| Scam detection on real message stream | 2.1 — _on_message | Requires live message flow | Run crawler, send message to monitored channel, verify WARNING log |
| Graceful shutdown on SIGINT/SIGTERM | 3.1 | Requires process signals | Start `python src/main.py`, press Ctrl+C, verify clean disconnect log |
| Exponential backoff reconnect | 2.1 — disconnect handling | Requires network interruption | Disconnect network while crawler runs, verify reconnect logs |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none needed)
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
